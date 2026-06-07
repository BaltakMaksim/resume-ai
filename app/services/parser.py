import PyPDF2
from io import BytesIO
def parse_resume_pdf(file_bytes: bytes) -> str:
    """Извлекает текст из PDF резюме"""
    try:
        pdf_reader =  PyPDF2.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Ошибка парсинга PDF: {str(e)}")