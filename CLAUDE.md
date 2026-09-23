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
- No public registration — an ADMIN creates operators (`python -m app.scripts.create_admin --login <wms login>` for the first admin).

## DB migrations
`00001` users · `00002` sku_registry · `00003` return_orders + order_lines · `00004` line_images ·
`00005` drops the SUPERVISOR role (roles: OPERATOR, ADMIN) · `00006` wms_orders ·
`00007` users log in with `wms_login` (case-insensitive) instead of an e-mail ·
`00008` return status + export statuses · `00009` a SKU has many EANs (`sku_eans`, each code unique) + `sku_imports` ·
`00010` work_logs (minutes per day).
Hand-written,
`down_revision` = previous, run on container start (`entrypoint.sh`).

## Tests
sqlite in-memory (`tests/conftest.py`, add new tables to `TEST_TABLES`); `admin_headers` /
`operator_headers` fixtures log in through the API.

## SKU import
Admin uploads the WMS export (`sku_ean.json`: `{"supplier_sku_id": EAN, "sku_id": reference, "description", "ecommerce": "Y|N"}` records)
on the "Produkty" page → `POST /api/sku-imports` (202) saves it to a temp file and runs `services/sku_import.py`
as a BackgroundTask; the page polls `GET /api/sku-imports/latest`. Upsert only, nothing is deleted:
new SKUs/codes are added, names updated, `ecommerce` → `is_parametrized` (a missing flag keeps the stored value),
an EAN listed under another SKU moves there (last row in the file wins). Bulk ORM insert/update in batches, one
transaction; ~600k rows. Manual SKU edits never move a code (409). One import at a time.

## Daily PDF form
"Raport dzienny" prints the paper form PL-FORM-CL-LM-038 ("ZWROTY OD KLIENTÓW") for one day:
`GET /api/reports/day-pdf?day=YYYY-MM-DD` returns it inline (any logged-in user). The blank form is a
scan (`app/assets/pdf/zwroty_od_klientow.jpg`, text in FreeSans from the same folder); reportlab only
draws onto it, so the coordinates in `services/day_report_pdf.py` belong to that scan — re-check the
rendered pages after touching them. Every line of every return with that `return_date` is printed
(open and closed), 17 rows per page, BO/WMS written once per return, `Liczba przyjętych` summed by
carrier on the last page. When the day has a work log, "CZAS WERYFIKACJI ZWROTÓW MIN: n" is printed under
the signature line. `/app/report-view.html?day=…` opens in a new tab and fetches the PDF with the bearer
token, so reloading that tab rebuilds the report; nothing is stored or cached (`Cache-Control: no-store`).

## Joby (work logs)
`/app/jobs.html` — minutes spent verifying returns, **one record per day** (`work_logs.work_date` is the
primary key); saving the same day again overwrites it and records who did. `GET/PUT/DELETE /api/work-logs/{day}`
plus a paged list, all for any logged-in user.

## Line images
Files live in `UPLOADS_DIR` (`./uploads` mounted at `/data/uploads` in docker; gitignored), named
`{bo_wms_number or brak}_{trade_reference}_{N}.{ext}` (`services/image_naming.py`). N runs 1..k per
(BO/WMS, reference) pair across all returns, since numbers repeat and "brak" is common; unsafe characters become
`~<hex>`. Changing an order's BO/WMS number, a line's SKU or a SKU's reference renames the files; deleting closes
gaps. `python -m app.scripts.rename_images` renames everything (idempotent). Type is checked from magic bytes (JPEG/PNG/WebP), size/count limits in `core/config/storage.py`.
`GET /api/images/{uuid}` needs the bearer token, so the cabinet shows photos from blob URLs.
Deleting a line or a return deletes its files after the DB commit.

## Return status and the report export
A return is `OPEN` while items are received and `CLOSED` when finished ("Zakończ"/"Następny zwrot" close it).
A closed return is locked (header, lines, photos, delete) until reopened. Only closed returns are exported.
`/api/integration/*` (`routers/integration.py`) hands out report rows (`services/report.py`: the report's exact
10 columns) and photos, each once: GET pending → write → POST `.../ack`, which sets `order_lines.exported_at` /
`line_images.downloaded_at`. Edits after export are not re-sent. Access: a logged-in user's token or the
`X-API-Key` header (`INTEGRATION_API_KEY`, for unattended jobs). The client is the Google Apps Script in
`integrations/google-apps-script/`.

## Frontend
Static multi-page cabinet in `frontend/`, served at `/app` (`app/cabinet.py`): HTML is `no-cache`,
JS/CSS get `?v=<mtime>`. One responsibility per page: `returns` (list) · `return-form` (header) ·
`return` (view) · `line` (scan → line + photos) · `line-view` (line + full-size photos) ·
`skus`/`sku-form` · `users`/`user-form`.
Polish UI; DOM built with `h()` (textContent only). Tables turn into cards below 960px.
Dev data: `uv run python -m app.scripts.seed_demo` (includes the sample report rows).

## Roadmap
1. Report export (row builder + writer; xlsx now, Google Sheets later; Celery)
