/**
 * Settings for the Zwroty e-com sync. Everything you may need to change lives here.
 * Apps Script shares one global scope across .gs files, so Code.gs sees these directly.
 */

/** Backend API root (no trailing slash). */
const API_BASE = "https://ecom-zwroty.piatek-magazyn.com/api";

/** The report tab: the number after #gid= in the spreadsheet URL. */
const REPORT_SHEET_GID = 0;

/** Drive folder for line photos: the id from the folder URL. */
const PHOTOS_FOLDER_ID = "1o5rc5eYQXJ1qSA1DgLmm7665ZrGOzYO3";

/** How many report rows / photos to take per request. */
const LINES_BATCH = 500;
const PHOTOS_BATCH = 20; // downloaded in parallel

/** Apps Script kills a run at 6 minutes; stop cleanly before that and let the user press again. */
const TIME_BUDGET_MS = 5 * 60 * 1000;

/** Column positions in the report layout (1 = A). */
const DATE_COLUMN = 1; // DATA ZWROTU
const TEXT_COLUMNS = [2, 3, 4]; // BO/WMS, Tempo, reference: keep "brak" and leading zeros exactly as sent
