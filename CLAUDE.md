# ecom_zwroty — project context for Claude

Internal warehouse CRM for returned e-commerce orders (single warehouse, mono-tenant).
Operator creates a return order (BO/WMS + Tempo numbers, return date), adds lines by EAN
(SKU, quantity, carrier, condition, damage description, remarks) and photos per line.
Output is a returns report (currently planned as xlsx, target is Google Sheets).

## Working rules
- **Do NOT commit/push/deploy unless explicitly asked — each time separately.** Small logical commits.
- **Never add co-authorship / "Generated with Claude"** to commits or GitHub. Author = the user.
- Communicate in **Ukrainian** unless asked otherwise.
- **Do not invent fields or features** beyond the spec — ask when unsure.
- Before saying "done": `uv run ruff check .`, `uv run ruff format .`, `uv run pytest -q` all green.

## Architecture (mirrors langup_backend)
router → service → repository → model (SQLAlchemy async) → Postgres. Pydantic `schemas/` at the
boundaries, DI via `Annotated` aliases in `app/dependencies.py`, custom exceptions in `app/core/exc`
mapped to HTTP codes in `handlers.py`.
New feature = one vertical: `model → migration → repository → schema → service → router (+ dependencies.py) → tests`.

## Domain decisions
- Code identifiers are **English**; Polish only in report headers / UI labels
  (PARCEL=paczka, PALLET=paleta, DAMAGED=uszkodzony, FULL_VALUE=pełnowartościowy, is_parametrized → tak/nie).
- Missing BO/WMS or Tempo number is stored as **NULL** and rendered as "brak"; numbers may repeat (no unique).
- `is_parametrized` belongs to the SKU; `remarks` (UWAGI) belongs to the order line.
- No public registration — an ADMIN creates operators (`python -m app.scripts.create_admin` for the first admin).

## DB migrations
`00001` users · `00002` sku_registry · `00003` return_orders + order_lines. Hand-written,
`down_revision` = previous, run on container start (`entrypoint.sh`).

## Tests
sqlite in-memory (`tests/conftest.py`, add new tables to `TEST_TABLES`); `admin_headers` /
`operator_headers` fixtures log in through the API.

## Roadmap
1. Line images (local docker volume)
2. Report export (row builder + writer; xlsx now, Google Sheets later; Celery)
3. Frontend (static `frontend/` served at `/app`)
