import asyncio
from app.api.routers.telegram import get_application

async def test():
    app = get_application()
    print("Application initialized successfully")

asyncio.run(test())
