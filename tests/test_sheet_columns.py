import asyncio
from app.services.google_sheets_service import _access_token, settings
import httpx
from urllib.parse import quote

async def main():
    token = await _access_token()
    spreadsheet_id = settings.google_sheet_id
    range_name = quote('Expenses!A1:F5', safe='')
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_name}'
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={'Authorization': f'Bearer {token}'},
        )
        print(response.json())

if __name__ == '__main__':
    asyncio.run(main())
