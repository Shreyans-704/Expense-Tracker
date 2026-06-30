import logging

from fastapi import APIRouter, HTTPException, status

from app.services.google_sheets_service import (
    GoogleSheetsError,
    append_expense,
    get_sheets_diagnostics,
    list_sheet_tabs,
    sample_expense,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/test-sheets")
async def test_sheets() -> dict[str, str]:
    try:
        updated_range = await append_expense(sample_expense())
    except GoogleSheetsError as exc:
        logger.exception("Failed to append sample expense to Google Sheets")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": str(exc),
                "troubleshooting": exc.troubleshooting,
            },
        ) from exc

    return {"status": "ok", "updated_range": updated_range}


@router.get("/test-sheets/diagnostics")
async def test_sheets_diagnostics() -> dict[str, str | bool | None]:
    return get_sheets_diagnostics()


@router.get("/test-sheets/tabs")
async def test_sheets_tabs() -> dict[str, list[str]]:
    try:
        tabs = await list_sheet_tabs()
    except GoogleSheetsError as exc:
        logger.exception("Failed to list Google Sheet tabs")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": str(exc),
                "troubleshooting": exc.troubleshooting,
            },
        ) from exc

    return {"tabs": tabs}
