# ecom_zwroty

CRM for registering returned e-commerce orders: an operator records the order header, adds lines
by EAN (with condition, carrier and damage description) and the data feeds the returns report.

Stack: Python 3.13, FastAPI (async), SQLAlchemy 2, Alembic, PostgreSQL, Docker, uv.

## Local development

```bash
uv sync
cp .env.sample .env        # set DATABASE_URL to a local Postgres
uv run alembic upgrade head
uv run python -m app.scripts.create_admin --login admin --full-name "Admin"
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Docker

```bash
cp .env.sample .env
docker compose up -d --build
docker compose exec app python -m app.scripts.create_admin --login admin --full-name "Admin"
```

## Checks

```bash
uv run ruff check . && uv run ruff format .
uv run pytest -q
```

## API

| Method | Path | Access |
|---|---|---|
| POST | `/api/auth/login` | public |
| GET | `/api/auth/me` | any user |
| POST/GET/PATCH | `/api/users` | ADMIN |
| GET/POST/PATCH | `/api/skus`, GET `/api/skus/by-ean/{ean}` | any user |
| POST/GET/PATCH/DELETE | `/api/returns`, `/api/returns/{uuid}` | any user |
| POST/PATCH/DELETE | `/api/returns/{uuid}/lines[/{line_uuid}]` | any user |
