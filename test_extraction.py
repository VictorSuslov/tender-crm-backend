import asyncio
from app.services.document_service import DocumentService

async def main():
    # Тест PDF
    try:
        text = DocumentService.extract_text_from_file("test.pdf")
        print(f"✓ PDF: извлечено {len(text)} символов")
        print(f"  Превью: {text[:200]}...")
    except Exception as e:
        print(f"✗ PDF: {e}")
    
    # Тест DOCX
    try:
        text = DocumentService.extract_text_from_file("test.docx")
        print(f"✓ DOCX: извлечено {len(text)} символов")
    except Exception as e:
        print(f"✗ DOCX: {e}")

if __name__ == "__main__":
    asyncio.run(main())