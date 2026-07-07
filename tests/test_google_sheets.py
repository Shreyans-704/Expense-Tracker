import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.logging import configure_logging
from app.services.google_sheets_service import GoogleSheetsError, append_expense, sample_expense


async def main() -> None:
    configure_logging()

    try:
        updated_range = await append_expense(sample_expense())
    except GoogleSheetsError as exc:
        logging.exception("Failed to append sample expense to Google Sheets")
        print(f"FAILED: {exc}")
        print("Troubleshooting:")
        for item in exc.troubleshooting:
            print(f"- {item}")
        raise SystemExit(1) from exc

    print(f"OK: appended sample expense to {updated_range}")


if __name__ == "__main__":
    asyncio.run(main())
