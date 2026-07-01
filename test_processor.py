import asyncio
from app.services.email_processor import test_email_processor

if __name__ == "__main__":
    asyncio.run(test_email_processor())