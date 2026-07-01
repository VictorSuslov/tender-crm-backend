import asyncio
from app.services.llm_analyzer import test_llm_analyzer

if __name__ == "__main__":
    asyncio.run(test_llm_analyzer())