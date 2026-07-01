import logging
from collections.abc import Mapping
import json
from urllib.parse import quote

import anyio
import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from app.core.config import settings

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
logger = logging.getLogger(__name__)


class GoogleSheetsError(RuntimeError):
    """Raised when an expense cannot be appended to Google Sheets."""

    def __init__(self, message: str, troubleshooting: list[str] | None = None):
        super().__init__(message)
        self.troubleshooting = troubleshooting or DEFAULT_TROUBLESHOOTING


DEFAULT_TROUBLESHOOTING = [
    "Confirm GOOGLE_SHEET_ID matches the ID in the Google Sheet URL.",
    "Confirm GOOGLE_SERVICE_ACCOUNT_FILE points to your credentials.json file.",
    "Share the Google Sheet with the service account client_email from credentials.json.",
    "Confirm the Google Sheets API is enabled in the Google Cloud project.",
    "Confirm GOOGLE_SHEETS_RANGE uses an existing tab name, for example Sheet1!A:F.",
]


def sample_expense() -> dict[str, object]:
    return {
        "date": "2026-06-30",
        "amount": 100,
        "item": "Test expense",
        "category": "Testing",
        "notes": "Sample row from Google Sheets integration test",
    }


async def get_last_expense_row(sheet_name: str) -> dict | None:
    """Find the last expense row, its row index, and content."""
    token = await _access_token()
    spreadsheet_id = _required_setting(settings.google_sheet_id, "GOOGLE_SHEET_ID")
    range_name = quote(f"{sheet_name}!A:F", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to fetch rows for undo")
        raise GoogleSheetsError("Failed to fetch rows from Google Sheets.") from exc

    data = response.json()
    values = data.get("values", [])

    # Empty or only header row
    if not values or len(values) <= 1:
        return None

    last_row_idx = len(values)  # 1-indexed for Sheets, len(values) is the last populated row
    last_row_data = values[-1]

    # Make sure we have at least amount and item
    if len(last_row_data) < 3:
        return None

    return {
        "row_index": last_row_idx,
        "date": last_row_data[0] if len(last_row_data) > 0 else "",
        "amount": last_row_data[1] if len(last_row_data) > 1 else "",
        "item": last_row_data[2] if len(last_row_data) > 2 else "",
        "category": last_row_data[3] if len(last_row_data) > 3 else "",
    }


async def delete_row(sheet_name: str, row_index: int) -> None:
    """Delete a specific row index (1-based) from a sheet."""
    token = await _access_token()
    spreadsheet_id = _required_setting(settings.google_sheet_id, "GOOGLE_SHEET_ID")

    # First get the sheet ID for the given sheet name
    url_get = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url_get,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise GoogleSheetsError("Failed to fetch spreadsheet metadata.") from exc

    data = response.json()
    sheet_id = None
    for sheet in data.get("sheets", []):
        if sheet.get("properties", {}).get("title") == sheet_name:
            sheet_id = sheet.get("properties", {}).get("sheetId")
            break

    if sheet_id is None:
        raise GoogleSheetsError(f"Sheet {sheet_name} not found.")

    # Execute batch update to delete the row
    # row_index is 1-based, Sheets API uses 0-based for startIndex/endIndex
    # e.g. row 2 is startIndex=1, endIndex=2
    url_batch = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate"
    payload = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": row_index - 1,
                        "endIndex": row_index
                    }
                }
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url_batch,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to delete row")
        raise GoogleSheetsError("Failed to delete row from Google Sheets.") from exc

async def undo_last_expense() -> dict | None:
    """Find and delete the last expense row. Returns the deleted expense data."""
    # Parse sheet name from GOOGLE_SHEETS_RANGE
    range_str = settings.google_sheets_range
    sheet_name = range_str.split("!")[0] if "!" in range_str else "Sheet1"

    last_expense = await get_last_expense_row(sheet_name)
    if not last_expense:
        return None

    await delete_row(sheet_name, last_expense["row_index"])
    return last_expense

async def append_expense(expense: dict) -> str:
    """Append an expense row to the configured Google Sheet.

    Expected keys: date, amount, item, category, notes.
    Returns the updated range reported by the Google Sheets API.
    """
    row = _expense_to_row(expense)
    token = await _access_token()
    spreadsheet_id = _required_setting(settings.google_sheet_id, "GOOGLE_SHEET_ID")
    range_name = quote(settings.google_sheets_range, safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}:append"
    payload = {"values": [row]}
    params = {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                params=params,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        google_error = _google_error_message(exc.response)
        logger.exception(
            "Google Sheets append failed. status=%s response=%s",
            exc.response.status_code,
            exc.response.text,
        )
        raise GoogleSheetsError(
            (
                f"Google Sheets rejected the append request with HTTP "
                f"{exc.response.status_code}: {google_error}"
            ),
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Google Sheets append request failed")
        raise GoogleSheetsError("Could not reach Google Sheets API.") from exc

    data = response.json()
    updated_range = data.get("updates", {}).get("updatedRange")
    logger.info("Appended expense to Google Sheets range %s", updated_range)
    return updated_range or settings.google_sheets_range


async def list_sheet_tabs() -> list[str]:
    token = await _access_token()
    spreadsheet_id = _required_setting(settings.google_sheet_id, "GOOGLE_SHEET_ID")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    params = {"fields": "sheets.properties.title"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        google_error = _google_error_message(exc.response)
        logger.exception(
            "Google Sheets tab lookup failed. status=%s response=%s",
            exc.response.status_code,
            exc.response.text,
        )
        raise GoogleSheetsError(
            (
                f"Google Sheets rejected the tab lookup with HTTP "
                f"{exc.response.status_code}: {google_error}"
            ),
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Google Sheets tab lookup request failed")
        raise GoogleSheetsError("Could not reach Google Sheets API.") from exc

    data = response.json()
    return [
        sheet.get("properties", {}).get("title")
        for sheet in data.get("sheets", [])
        if sheet.get("properties", {}).get("title")
    ]


async def _access_token() -> str:
    return await anyio.to_thread.run_sync(_blocking_access_token)


def _blocking_access_token() -> str:
    credentials_file = _required_setting(
        settings.google_service_account_file,
        "GOOGLE_SERVICE_ACCOUNT_FILE",
    )

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file,
            scopes=[SHEETS_SCOPE],
        )
        credentials.refresh(Request())
    except FileNotFoundError as exc:
        logger.exception("Google service account file not found: %s", credentials_file)
        raise GoogleSheetsError(
            "Google service account credentials file was not found.",
            troubleshooting=[
                "Place credentials.json in the project root, or update GOOGLE_SERVICE_ACCOUNT_FILE.",
                "Use a path relative to where you start uvicorn, or use an absolute path.",
            ],
        ) from exc
    except Exception as exc:
        logger.exception("Could not load or refresh Google service account credentials")
        raise GoogleSheetsError("Could not authenticate with Google Sheets.") from exc

    if not credentials.token:
        raise GoogleSheetsError("Google authentication did not return an access token.")
    return credentials.token


def get_sheets_diagnostics() -> dict[str, str | bool | None]:
    credentials_file = settings.google_service_account_file or "credentials.json"
    diagnostics: dict[str, str | bool | None] = {
        "google_sheet_id_configured": bool(settings.google_sheet_id),
        "google_sheet_id_suffix": settings.google_sheet_id[-6:] if settings.google_sheet_id else None,
        "google_sheets_range": settings.google_sheets_range,
        "google_service_account_file": credentials_file,
        "credentials_file_exists": False,
        "service_account_email": None,
        "project_id": None,
    }

    try:
        with open(credentials_file, encoding="utf-8") as file:
            credentials = json.load(file)
    except FileNotFoundError:
        return diagnostics

    diagnostics["credentials_file_exists"] = True
    diagnostics["service_account_email"] = credentials.get("client_email")
    diagnostics["project_id"] = credentials.get("project_id")
    return diagnostics


def _expense_to_row(expense: Mapping[str, object]) -> list[object]:
    missing = [
        field
        for field in ("date", "amount", "item", "category", "notes")
        if field not in expense
    ]
    if missing:
        raise GoogleSheetsError(f"Expense is missing required fields: {', '.join(missing)}")

    return [
        expense["date"],
        expense["amount"],
        expense["item"],
        expense["category"],
        expense["notes"],
    ]


def _required_setting(value: str | None, name: str) -> str:
    if not value:
        raise GoogleSheetsError(f"{name} is required.")
    return value


def _google_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text

    error = data.get("error", {})
    message = error.get("message")
    reason = None
    details = error.get("details") or error.get("errors") or []
    if details and isinstance(details, list):
        reason = details[0].get("reason") if isinstance(details[0], dict) else None

    if message and reason:
        return f"{message} ({reason})"
    return message or response.text



async def get_current_balance() -> str | None:
    """Get the current balance from the Settings sheet."""
    token = await _access_token()
    spreadsheet_id = _required_setting(settings.google_sheet_id, "GOOGLE_SHEET_ID")
    range_name = quote("Settings!A:B", safe="")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to fetch Settings sheet")
        raise GoogleSheetsError("Failed to fetch Settings from Google Sheets.") from exc

    data = response.json()
    for row in data.get("values", []):
        if row and row[0] == "Current Balance":
            return row[1] if len(row) > 1 else None
    return None


async def update_current_balance(amount: float) -> None:
    """Update the current balance in the Settings sheet."""
    token = await _access_token()
    spreadsheet_id = _required_setting(settings.google_sheet_id, "GOOGLE_SHEET_ID")
    range_name = quote("Settings!A:B", safe="")
    url_get = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url_get,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to fetch Settings sheet for update")
        raise GoogleSheetsError("Failed to fetch Settings for update.") from exc

    data = response.json()
    row_idx = None
    for i, row in enumerate(data.get("values", [])):
        if row and row[0] == "Current Balance":
            row_idx = i + 1
            break
            
    if row_idx is None:
        raise GoogleSheetsError("Could not find 'Current Balance' row in Settings sheet.")

    update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/Settings!B{row_idx}?valueInputOption=USER_ENTERED"
    payload = {"values": [[str(amount)]]}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            put_response = await client.put(
                update_url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            put_response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("Failed to update balance")
        raise GoogleSheetsError("Failed to update balance in Google Sheets.") from exc


class GoogleSheetsService:
    async def append_expense(self, expense: dict) -> str:
        return await append_expense(expense)
