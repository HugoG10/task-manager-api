# Task Manager API

REST API for personal tasks. Users register, log in with JWT, and manage their own tasks (title, description, status, priority, due date). Other users cannot see or change your tasks.

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Live on Render: [https://task-manager-api-bxsj.onrender.com/docs](https://task-manager-api-bxsj.onrender.com/docs)

## Resume bullets

- Built a FastAPI REST API with JWT auth, bcrypt password hashing, and per-user task isolation
- Modeled tasks with status, priority, and due dates, including list filtering by status
- Covered auth, CRUD, and cross-user 404s with pytest; containerized the API and PostgreSQL with Docker Compose

## Stack

FastAPI, SQLAlchemy 2, Pydantic v2, JWT, PostgreSQL (Docker) / SQLite (local + tests)

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The API listens on `http://localhost:8000`. SQLite is the default database (`app.db`).

## Run with Docker (PostgreSQL)

```bash
docker compose up --build
```

## Example

```bash
# Register
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"hugo@example.com","password":"secret123"}'

# Login (OAuth2 form; username is the email)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=hugo@example.com&password=secret123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Create a task
curl -s -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Ship the API","status":"todo","priority":"high","due_date":"2026-09-01"}'
```

## API

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| `GET` | `/health` | no | Liveness |
| `POST` | `/auth/register` | no | `{email, password}` → `201` |
| `POST` | `/auth/login` | no | form `username` + `password` → JWT |
| `GET` | `/auth/me` | yes | Current user |
| `GET` | `/tasks?status=` | yes | List own tasks, optional `todo` / `in_progress` / `done` |
| `POST` | `/tasks` | yes | Create (`201`) |
| `GET` | `/tasks/{id}` | yes | Fetch one |
| `PATCH` | `/tasks/{id}` | yes | Partial update |
| `DELETE` | `/tasks/{id}` | yes | `204` |

Missing tasks and tasks owned by someone else both return `404`.

## Tests

```bash
source .venv/bin/activate
pytest
```
