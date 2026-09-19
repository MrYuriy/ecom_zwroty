# Google Sheet export (Apps Script)

A button in the report spreadsheet that pulls **new report rows** (closed returns only) into the report tab
and **new line photos** into a Drive folder, using `/api/integration/*`.

- Log in with a WMS login + password (any active user); the dialog masks the password.
- Rows are appended in the report's column order; BO/WMS, Tempo and reference are written as text.
- Photos keep their server names (`{BO/WMS}_{reference}_{N}.jpg`); a file already in the folder is not duplicated.
- Every batch is acknowledged only after it is written, so re-running never duplicates rows or photos.
  A run stops before Apps Script's 6-minute limit and reports what is left; press the button again to finish.

## Setup (once)

1. Open the spreadsheet → **Extensions → Apps Script**.
2. Create the files and paste the contents from this folder:
   - `Config.gs` — all settings
   - `Code.gs` — the sync itself
   - `LoginDialog.html` (File → + → HTML, name it `LoginDialog`)
   - `appsscript.json`: Project Settings → tick **Show "appsscript.json" manifest file**, then replace it.
3. Check `Config.gs` (`API_BASE`, `REPORT_SHEET_GID`, `PHOTOS_FOLDER_ID`).
4. Save, reload the spreadsheet: a **Zwroty e-com** menu appears. The first run asks for permissions
   (the sheet, Drive, external requests, dialogs).
5. Optional button: **Insert → Drawing**, draw a button, then **⋮ → Assign script** → `showSyncDialog`.

Whoever presses the button needs edit access to the spreadsheet and the Drive folder.

**Zwroty e-com → Sprawdź reguły arkusza** writes nothing; it prints the data validation of each report
column, which is what to look at when the sheet rejects a value.
