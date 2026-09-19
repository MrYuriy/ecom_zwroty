/**
 * Zwroty e-com → Google Sheet + Google Drive.
 *
 * One button: log in, then
 *   1) append new report rows (closed returns only) to the report tab, in the report's column order;
 *   2) download new line photos into the Drive folder.
 * Each batch is acknowledged back to the API only after it was written, so nothing is duplicated and
 * nothing is lost: pressing the button again simply continues where the previous run stopped.
 */

// ===== Settings =====
const API_BASE = "https://ecom-zwroty.piatek-magazyn.com/api";
const REPORT_SHEET_GID = 0; // the tab from ...#gid=0 in the sheet's URL
const PHOTOS_FOLDER_ID = "1o5rc5eYQXJ1qSA1DgLmm7665ZrGOzYO3";

const LINES_BATCH = 500;
const PHOTOS_BATCH = 20; // downloaded in parallel
const TIME_BUDGET_MS = 5 * 60 * 1000; // Apps Script kills a run at 6 minutes; stop cleanly before that
const DATE_COLUMN = 1; // DATA ZWROTU
const TEXT_COLUMNS = [2, 3, 4]; // BO/WMS, Tempo, reference: keep "brak" and leading zeros exactly as sent

// ===== Menu and dialog =====

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Zwroty e-com")
    .addItem("Pobierz zwroty i zdjęcia", "showSyncDialog")
    .addToUi();
}

/** Assign this function to a button (Insert → Drawing → ⋮ → Assign script). */
function showSyncDialog() {
  const html = HtmlService.createHtmlOutputFromFile("LoginDialog").setWidth(380).setHeight(330);
  SpreadsheetApp.getUi().showModalDialog(html, "Zwroty e-com");
}

/** Called from the dialog. Returns the summary shown to the user; a thrown Error is shown as the failure. */
function runSync(wmsLogin, password) {
  const started = Date.now();
  const token = apiLogin(wmsLogin, password);
  const lines = syncReportLines(token, started);
  const photos = syncPhotos(token, started);

  const parts = [`Dopisano wierszy: ${lines.written}`, `Zapisano zdjęć: ${photos.saved}`];
  if (photos.alreadyInFolder) parts.push(`Zdjęcia już w folderze: ${photos.alreadyInFolder}`);
  if (photos.failed.length) parts.push(`Nie udało się pobrać: ${photos.failed.join(", ")}`);
  if (lines.remaining || photos.remaining) {
    parts.push(
      `Pozostało (limit czasu): ${lines.remaining} wierszy, ${photos.remaining} zdjęć — kliknij ponownie, aby dokończyć.`,
    );
  }
  return parts.join("\n");
}

// ===== Report rows =====

function syncReportLines(token, started) {
  const sheet = reportSheet();
  let written = 0;
  let remaining = 0;

  while (true) {
    const page = apiRequest("get", `/integration/report-lines?limit=${LINES_BATCH}`, token);
    if (!page.items.length) {
      remaining = 0;
      break;
    }
    if (sheet.getLastRow() === 0) sheet.appendRow(page.columns);

    const rows = page.items.map((item) => item.row);
    const firstRow = sheet.getLastRow() + 1;
    TEXT_COLUMNS.forEach((col) => sheet.getRange(firstRow, col, rows.length, 1).setNumberFormat("@"));
    sheet.getRange(firstRow, DATE_COLUMN, rows.length, 1).setNumberFormat("yyyy-mm-dd");
    sheet.getRange(firstRow, 1, rows.length, page.columns.length).setValues(rows);
    SpreadsheetApp.flush(); // make sure the rows are really saved before telling the API they are

    apiRequest("post", "/integration/report-lines/ack", token, {
      line_uuids: page.items.map((item) => item.line_uuid),
    });
    written += rows.length;
    remaining = page.remaining;
    if (!remaining || outOfTime(started)) break;
  }
  return { written, remaining };
}

function reportSheet() {
  const sheet = SpreadsheetApp.getActive()
    .getSheets()
    .find((s) => s.getSheetId() === REPORT_SHEET_GID);
  if (!sheet) throw new Error(`Nie znaleziono arkusza z gid=${REPORT_SHEET_GID}.`);
  return sheet;
}

// ===== Photos =====

function syncPhotos(token, started) {
  const folder = DriveApp.getFolderById(PHOTOS_FOLDER_ID);
  const result = { saved: 0, alreadyInFolder: 0, failed: [], remaining: 0 };

  while (!outOfTime(started)) {
    const page = apiRequest("get", `/integration/images?limit=${PHOTOS_BATCH}`, token);
    if (!page.items.length) {
      result.remaining = 0;
      break;
    }

    const responses = UrlFetchApp.fetchAll(
      page.items.map((item) => ({
        url: `${API_BASE}/integration/images/${item.image_uuid}`,
        headers: { Authorization: `Bearer ${token}` },
        muteHttpExceptions: true,
      })),
    );

    const delivered = [];
    page.items.forEach((item, i) => {
      if (responses[i].getResponseCode() !== 200) {
        result.failed.push(item.file_name);
        return;
      }
      // A file may already be there if an earlier run saved it but could not acknowledge it.
      if (folder.getFilesByName(item.file_name).hasNext()) {
        result.alreadyInFolder += 1;
      } else {
        folder.createFile(responses[i].getBlob().setName(item.file_name));
        result.saved += 1;
      }
      delivered.push(item.image_uuid);
    });

    if (delivered.length) {
      apiRequest("post", "/integration/images/ack", token, { image_uuids: delivered });
    }
    result.remaining = page.remaining + (page.items.length - delivered.length);
    // A failed photo stays pending and would come back first; stop instead of looping on it.
    if (!page.remaining || delivered.length < page.items.length) break;
  }
  return result;
}

// ===== API =====

function apiLogin(wmsLogin, password) {
  if (!wmsLogin || !password) throw new Error("Podaj login WMS i hasło.");
  const response = UrlFetchApp.fetch(`${API_BASE}/auth/login`, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify({ wms_login: wmsLogin.trim(), password }),
    muteHttpExceptions: true,
  });
  if (response.getResponseCode() === 401) throw new Error("Nieprawidłowy login lub hasło.");
  if (response.getResponseCode() !== 200) throw apiError(response);
  return JSON.parse(response.getContentText()).access_token;
}

function apiRequest(method, path, token, body) {
  const options = {
    method,
    headers: { Authorization: `Bearer ${token}` },
    muteHttpExceptions: true,
  };
  if (body !== undefined) {
    options.contentType = "application/json";
    options.payload = JSON.stringify(body);
  }
  const response = UrlFetchApp.fetch(`${API_BASE}${path}`, options);
  if (response.getResponseCode() === 401) throw new Error("Sesja wygasła lub brak dostępu — zaloguj się ponownie.");
  if (response.getResponseCode() >= 300) throw apiError(response);
  return JSON.parse(response.getContentText());
}

function apiError(response) {
  return new Error(`Błąd serwera ${response.getResponseCode()}: ${response.getContentText().slice(0, 200)}`);
}

function outOfTime(started) {
  return Date.now() - started > TIME_BUDGET_MS;
}
