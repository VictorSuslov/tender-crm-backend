import asyncio
from app.services.imap_service import test_imap_connection

if __name__ == "__main__":
    asyncio.run(test_imap_connection())