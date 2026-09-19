/**
 * Zwroty e-com → Google Sheet + Google Drive.
 *
 * One button: log in, then
 *   1) append new report rows (closed returns only) to the report tab, in the report's column order;
 *   2) download new line photos into the Drive folder.
 * Each batch is acknowledged back to the API only after it was written, so nothing is duplicated and
 * nothing is lost: pressing the button again simply continues where the previous run stopped.
 *
 * Every step is logged; the log is shown in the dialog and in Apps Script → Executions.
 * Settings (API address, sheet tab, Drive folder, batch sizes) live in Config.gs.
 */

// ===== Menu and dialog =====

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("Zwroty e-com")
    .addItem("Pobierz zwroty i zdjęcia", "showSyncDialog")
    .addItem("Sprawdź reguły arkusza", "checkSheetRules")
    .addToUi();
}

/** Assign this function to a button (Insert → Drawing → ⋮ → Assign script). */
function showSyncDialog() {
  const html = HtmlService.createHtmlOutputFromFile("LoginDialog").setWidth(460).setHeight(460);
  SpreadsheetApp.getUi().showModalDialog(html, "Zwroty e-com");
}

/** Diagnostics only: shows what data validation the next free row expects. Writes nothing. */
function checkSheetRules() {
  LOG = [];
  const sheet = reportSheet();
  const row = sheet.getLastRow() + 1;
  log(`arkusz „${sheet.getName()}”: wierszy ${sheet.getLastRow()}/${sheet.getMaxRows()}, kolumn ${sheet.getMaxColumns()}`);
  log(`reguły w wierszu ${row}:`);

  const rules = sheet.getRange(row, 1, 1, Math.min(10, sheet.getMaxColumns())).getDataValidations()[0];
  rules.forEach((rule, index) => {
    const column = String.fromCharCode(65 + index);
    if (!rule) {
      log(`  ${column}: brak reguły`);
      return;
    }
    let description;
    try {
      const args = rule.getCriteriaValues();
      const allowed = args[0] && args[0].getValues ? args[0].getValues().flat() : args[0];
      description = `${rule.getCriteriaType()} → ${JSON.stringify(allowed)}`;
    } catch (error) {
      description = `${rule.getCriteriaType()} → NIE MOŻNA ODCZYTAĆ (${error.message})`;
    }
    log(`  ${column}: ${description}`);
  });

  SpreadsheetApp.getUi().alert("Reguły arkusza", LOG.join("\n"), SpreadsheetApp.getUi().ButtonSet.OK);
}

// ===== Logging =====

let LOG = [];

function log(message) {
  const line = `${new Date().toISOString().slice(11, 19)}  ${message}`;
  LOG.push(line);
  console.log(line);
}

/** Names the stage in the error: Google's own errors (e.g. "Range not found") carry no context. */
function step(name, action) {
  log(`→ ${name}`);
  try {
    const result = action();
    log(`✓ ${name}`);
    return result;
  } catch (error) {
    log(`✗ ${name}: ${error.message}`);
    console.error(error.stack || error.message);
    throw new Error(`Błąd na etapie „${name}”: ${error.message}`);
  }
}

/** Called from the dialog. Always returns {ok, message, log} — the dialog shows the log either way. */
function runSync(wmsLogin, password) {
  LOG = [];
  const started = Date.now();
  try {
    const token = step("logowanie", () => apiLogin(wmsLogin, password));
    const lines = step("zapis wierszy do arkusza", () => syncReportLines(token, started));
    const photos = step("pobieranie zdjęć na Dysk", () => syncPhotos(token, started));

    const parts = [`Dopisano wierszy: ${lines.written}`, `Zapisano zdjęć: ${photos.saved}`];
    if (photos.alreadyInFolder) parts.push(`Zdjęcia już w folderze: ${photos.alreadyInFolder}`);
    if (photos.failed.length) parts.push(`Nie udało się pobrać: ${photos.failed.join(", ")}`);
    if (lines.remaining || photos.remaining) {
      parts.push(
        `Pozostało (limit czasu): ${lines.remaining} wierszy, ${photos.remaining} zdjęć — kliknij ponownie.`,
      );
    }
    return { ok: true, message: parts.join("\n"), log: LOG.join("\n") };
  } catch (error) {
    return { ok: false, message: error.message, log: LOG.join("\n") };
  }
}

// ===== Report rows =====

function syncReportLines(token, started) {
  const sheet = reportSheet();
  log(`arkusz „${sheet.getName()}”: wierszy ${sheet.getLastRow()}/${sheet.getMaxRows()}, kolumn ${sheet.getMaxColumns()}`);
  let written = 0;
  let remaining = 0;

  while (true) {
    const page = apiRequest("get", `/integration/report-lines?limit=${LINES_BATCH}`, token);
    log(`pobrano wierszy: ${page.items.length}, pozostało na serwerze: ${page.remaining}`);
    if (!page.items.length) {
      remaining = 0;
      break;
    }
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(page.columns);
      log("arkusz był pusty — dopisano nagłówek");
    }

    const firstRow = sheet.getLastRow() + 1;
    ensureRows(sheet, firstRow + page.items.length - 1);
    ensureColumns(sheet, page.columns.length);
    const target = sheet.getRange(firstRow, 1, page.items.length, page.columns.length);
    log(`zapis do ${target.getA1Notation()}`);

    // Checked before anything is written, so a mismatch leaves the sheet untouched.
    const rows = fitToValidation(
      target,
      page.items.map((item) => item.row),
      page.columns,
    );
    TEXT_COLUMNS.forEach((col) => sheet.getRange(firstRow, col, rows.length, 1).setNumberFormat("@"));
    sheet.getRange(firstRow, DATE_COLUMN, rows.length, 1).setNumberFormat("yyyy-mm-dd");
    target.setValues(rows);
    SpreadsheetApp.flush(); // make sure the rows are really saved before telling the API they are
    log(`zapisano ${rows.length} wierszy`);

    apiRequest("post", "/integration/report-lines/ack", token, {
      line_uuids: page.items.map((item) => item.line_uuid),
    });
    log("potwierdzono zapis na serwerze");
    written += rows.length;
    remaining = page.remaining;
    if (!remaining) break;
    if (outOfTime(started)) {
      log("limit czasu — przerywam wiersze");
      break;
    }
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

function ensureRows(sheet, lastNeededRow) {
  const missing = lastNeededRow - sheet.getMaxRows();
  if (missing > 0) {
    sheet.insertRowsAfter(sheet.getMaxRows(), missing);
    log(`dodano ${missing} wierszy do arkusza`);
  }
}

function ensureColumns(sheet, neededColumns) {
  const missing = neededColumns - sheet.getMaxColumns();
  if (missing > 0) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), missing);
    log(`dodano ${missing} kolumn do arkusza`);
  }
}

/**
 * Makes our values pass the sheet's own data validation (drop-downs, checkboxes):
 * "tak" becomes "TAK"/"Tak" from the list, or a ticked checkbox. Throws if a value has no match.
 */
function fitToValidation(range, rows, columns) {
  let rules;
  try {
    rules = range.getDataValidations();
  } catch (error) {
    // A broken rule (e.g. a list pointing at a deleted range) — write the values unchanged.
    log(`nie można odczytać reguł arkusza (${error.message}) — zapisuję wartości bez zmian`);
    return rows;
  }
  let adapted = 0;
  const values = rows.map((row, r) =>
    row.map((value, c) => {
      if (!rules[r][c]) return value;
      let fitted = value;
      try {
        fitted = fitValue(rules[r][c], value, columns[c]);
      } catch (error) {
        if (error.message.indexOf("nie pasuje do listy") !== -1) throw error;
        log(`kolumna „${columns[c]}”: nie można odczytać reguły (${error.message}) — wartość bez zmian`);
        return value;
      }
      if (fitted !== value) adapted += 1;
      return fitted;
    }),
  );
  if (adapted) log(`dopasowano ${adapted} wartości do reguł sprawdzania danych`);
  return values;
}

function fitValue(rule, value, column) {
  const criteria = SpreadsheetApp.DataValidationCriteria;
  const type = rule.getCriteriaType();
  const args = rule.getCriteriaValues();

  if (type === criteria.CHECKBOX) {
    // A plain checkbox has no values (TRUE/FALSE); a custom one has [checked, unchecked].
    const checked = args.length ? args[0] : true;
    const unchecked = args.length > 1 ? args[1] : false;
    return String(value).trim().toLowerCase() === "tak" ? checked : unchecked;
  }

  let allowed = null;
  if (type === criteria.VALUE_IN_LIST) allowed = args[0];
  if (type === criteria.VALUE_IN_RANGE) {
    try {
      allowed = args[0]
        .getValues()
        .flat()
        .filter((option) => option !== "");
    } catch (error) {
      log(`nie można odczytać listy dla kolumny „${column}” (${error.message}) — zapisuję wartość bez zmian`);
      allowed = null;
    }
  }
  if (!allowed || value === "" || value === null) return value;

  const wanted = String(value).trim().toLowerCase();
  const match = allowed.find((option) => String(option).trim().toLowerCase() === wanted);
  if (match === undefined) {
    throw new Error(
      `Kolumna „${column}”: wartość „${value}” nie pasuje do listy w arkuszu (${allowed.join(", ")}). ` +
        "Nic nie zapisano.",
    );
  }
  return match;
}

// ===== Photos =====

function syncPhotos(token, started) {
  const folder = DriveApp.getFolderById(PHOTOS_FOLDER_ID);
  log(`folder na Dysku: „${folder.getName()}”`);
  const result = { saved: 0, alreadyInFolder: 0, failed: [], remaining: 0 };

  while (!outOfTime(started)) {
    const page = apiRequest("get", `/integration/images?limit=${PHOTOS_BATCH}`, token);
    log(`pobrano listę zdjęć: ${page.items.length}, pozostało na serwerze: ${page.remaining}`);
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
        log(`✗ ${item.file_name}: HTTP ${responses[i].getResponseCode()}`);
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
    log(`zapisano ${result.saved}, pominięto istniejące ${result.alreadyInFolder}`);

    if (delivered.length) {
      apiRequest("post", "/integration/images/ack", token, { image_uuids: delivered });
      log(`potwierdzono ${delivered.length} zdjęć`);
    }
    result.remaining = page.remaining + (page.items.length - delivered.length);
    // A failed photo stays pending and would come back first; stop instead of looping on it.
    if (!page.remaining || delivered.length < page.items.length) break;
  }
  if (outOfTime(started)) log("limit czasu — przerywam zdjęcia");
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
  log(`${method.toUpperCase()} ${path} → ${response.getResponseCode()}`);
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
