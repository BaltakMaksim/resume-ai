import PyPDF2
from io import BytesIO
from docx import Document


def parse_resume(file_bytes: bytes, filename: str) -> str:
    """Парсит PDF или DOCX файл и возвращает текст"""
    
    ext = filename.lower().split('.')[-1]
    
    if ext == 'pdf':
        return parse_pdf(file_bytes)
    elif ext == 'docx':
        return parse_docx(file_bytes)
    elif ext == 'doc':
        raise ValueError(
            "Старый формат .doc не поддерживается. "
            "Пожалуйста, сохрани файл как .docx в Word (Файл → Сохранить как → DOCX) "
            "или вставь текст резюме вручную."
        )
    else:
        raise ValueError(f"Неподдерживаемый формат: {ext}. Используйте PDF или DOCX")


def parse_pdf(file_bytes: bytes) -> str:
    """Извлекает текст из PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file_bytes))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Ошибка парсинга PDF: {str(e)}")


def parse_docx(file_bytes: bytes) -> str:
    """Извлекает текст из DOCX"""
    try:
        doc = Document(BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text.strip()
    except Exception as e:
        error_msg = str(e)
        if "not a zip file" in error_msg.lower():
            raise ValueError(
                "Файл повреждён или имеет неправильный формат. "
                "Пожалуйста, открой файл в Word и сохрани как .docx"
            )
        else:
            raise ValueError(f"Ошибка парсинга DOCX: {error_msg}")