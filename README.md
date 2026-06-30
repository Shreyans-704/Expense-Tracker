# Expense Tracker Backend

FastAPI backend with Google Sheets persistence for expense rows.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Environment

Use the existing `.env` file and set:

```text
GOOGLE_SHEET_ID
GOOGLE_SERVICE_ACCOUNT_FILE
GOOGLE_SHEETS_RANGE
```

Use a Google Service Account credentials file such as `credentials.json`, then share the target spreadsheet with the service account email. Set `GOOGLE_SHEETS_RANGE` to an existing sheet tab, for example `Sheet1!A:F`.

## Test Google Sheets

Put your service account JSON at the path configured by `GOOGLE_SERVICE_ACCOUNT_FILE`, then start the server from the project root:

```bash
uvicorn app.main:app --reload
```

In another terminal, call:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/test-sheets
```

The endpoint appends a sample row with `Date`, `Amount`, `Item`, `Category`, `Necessary`, and `Notes`.

You can also test without starting FastAPI:

```bash
python scripts/test_google_sheets.py
```

If the append fails, check the server or script logs. Common fixes:

- Share the Google Sheet with the `client_email` inside `credentials.json`.
- Confirm `GOOGLE_SHEET_ID` is the long ID from the spreadsheet URL.
- Confirm `GOOGLE_SERVICE_ACCOUNT_FILE` points to the real credentials file.
- Confirm the Google Sheets API is enabled in the same Google Cloud project.
- Confirm `GOOGLE_SHEETS_RANGE` uses an existing sheet tab, such as `Expenses!A:F`.

## Project Layout

```text
app/
  api/routers/      FastAPI route modules
  core/             config, logging, middleware
  schemas/          Pydantic request/response schemas
  services/         Google Sheets integration and app services
```
=======
# Expense-Tracker

