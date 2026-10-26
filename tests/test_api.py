import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register_and_login(client: TestClient, email: str, password: str = "secret123") -> dict[str, str]:
    register = client.post("/auth/register", json={"email": email, "password": password})
    assert register.status_code == 201
    login = client.post("/auth/login", data={"username": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_login_and_me(client: TestClient) -> None:
    register = client.post(
        "/auth/register",
        json={"email": "hugo@example.com", "password": "secret123"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == "hugo@example.com"

    duplicate = client.post(
        "/auth/register",
        json={"email": "hugo@example.com", "password": "secret123"},
    )
    assert duplicate.status_code == 409

    login = client.post(
        "/auth/login",
        data={"username": "hugo@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "hugo@example.com"


def test_task_crud_and_status_filter(client: TestClient) -> None:
    headers = _register_and_login(client, "hugo@example.com")

    created = client.post(
        "/tasks",
        json={
            "title": "Write README",
            "description": "Make it recruiter-friendly",
            "status": "todo",
            "priority": "high",
            "due_date": "2026-09-01",
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    task_id = body["id"]
    assert body["title"] == "Write README"
    assert body["status"] == "todo"
    assert body["priority"] == "high"
    assert body["due_date"] == "2026-09-01"

    listed = client.get("/tasks", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    client.post(
        "/tasks",
        json={"title": "Ship it", "status": "done"},
        headers=headers,
    )
    filtered = client.get("/tasks", params={"status": "todo"}, headers=headers)
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["title"] == "Write README"

    updated = client.patch(
        f"/tasks/{task_id}",
        json={"status": "in_progress", "title": "Draft README"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["title"] == "Draft README"

    fetched = client.get(f"/tasks/{task_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Draft README"

    deleted = client.delete(f"/tasks/{task_id}", headers=headers)
    assert deleted.status_code == 204

    missing = client.get(f"/tasks/{task_id}", headers=headers)
    assert missing.status_code == 404


def test_users_cannot_access_each_others_tasks(client: TestClient) -> None:
    hugo = _register_and_login(client, "hugo@example.com")
    other = _register_and_login(client, "other@example.com")

    created = client.post("/tasks", json={"title": "Hugo only"}, headers=hugo)
    assert created.status_code == 201
    task_id = created.json()["id"]

    listed = client.get("/tasks", headers=other)
    assert listed.status_code == 200
    assert listed.json() == []

    assert client.get(f"/tasks/{task_id}", headers=other).status_code == 404
    assert client.patch(f"/tasks/{task_id}", json={"title": "Nope"}, headers=other).status_code == 404
    assert client.delete(f"/tasks/{task_id}", headers=other).status_code == 404

    still_there = client.get(f"/tasks/{task_id}", headers=hugo)
    assert still_there.status_code == 200
    assert still_there.json()["title"] == "Hugo only"
