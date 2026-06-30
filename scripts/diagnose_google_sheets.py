import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.google_sheets_service import get_sheets_diagnostics


if __name__ == "__main__":
    diagnostics = get_sheets_diagnostics()
    for key, value in diagnostics.items():
        print(f"{key}: {value}")
