# Business CRUD API

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

On macOS/Linux, activate with:
```bash
source .venv/bin/activate
```

Open http://127.0.0.1:8000/docs to test endpoints.

## Endpoint groups

- `/stateless/sync/businesses` — SQLite-backed CRUD, sync functions
- `/stateless/async/businesses` — SQLite-backed CRUD, async functions
- `/stateful/sync/businesses` — in-memory CRUD, sync functions
- `/stateful/async/businesses` — in-memory CRUD, async functions

Use POST to create, GET to read, PUT to replace/update, and DELETE to remove.

Example request body:
```json
{
  "name": "Desale Electronics",
  "owner": "Rajan",
  "category": "Electronics",
  "revenue": 125000.50
}
```

## Important notes

“Stateless” here means requests do not depend on a stored client session. The API still stores business records in SQLite so CRUD data survives restarts. “Stateful” here demonstrates server-side in-memory resource state, which remains available between requests while the process runs but is lost when it restarts. These are teaching examples, not production-ready multi-user services. For production, add authentication, authorization, migrations, tests, logging, and concurrency considerations.
