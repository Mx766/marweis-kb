"""Extract searchable text content from document files (PDF, Word, Excel, text)."""
import io
import logging
import re

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 100_000  # max chars to store


def _sanitize(text: str) -> str:
    """Remove null bytes, surrogates, and other characters PostgreSQL can't store in UTF8."""
    # Strip lone surrogates which are invalid UTF-8
    text = re.sub(r'[\ud800-\udfff]', '', text)
    return text.replace('\x00', '').replace('�', '')[:MAX_CONTENT_LENGTH]


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text content from a file. Returns empty string on failure."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    try:
        if ext == 'pdf':
            return _sanitize(_extract_pdf(file_bytes))
        elif ext in ('docx',):
            return _sanitize(_extract_docx(file_bytes))
        elif ext in ('doc',):
            return _sanitize(_extract_doc(file_bytes))
        elif ext in ('xlsx',):
            return _sanitize(_extract_xlsx(file_bytes))
        elif ext in ('xls',):
            return _sanitize(_extract_xls(file_bytes))
        elif ext in ('txt', 'md', 'csv', 'log'):
            return _sanitize(_extract_text(file_bytes))
        else:
            return ''
    except Exception:
        logger.warning(f"Content extraction failed for {filename}", exc_info=True)
        return ''


def _extract_pdf(data: bytes) -> str:
    """Extract text from PDF using PyPDF2, fallback to pdfplumber."""
    parts = []
    # Try PyPDF2 first (fast)
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        result = '\n'.join(parts).strip()
        if len(result) > 100:
            return result[:MAX_CONTENT_LENGTH]
    except Exception:
        pass

    # Fallback: pdfplumber (slower but better for scanned docs)
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
        result = '\n'.join(parts).strip()
        return result[:MAX_CONTENT_LENGTH]
    except Exception:
        pass

    return ''


def _extract_docx(data: bytes) -> str:
    """Extract text from Word .docx files."""
    from docx import Document
    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    # Also extract table content
    for table in doc.tables:
        for row in table.rows:
            row_text = ' | '.join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                parts.append(row_text)
    return '\n'.join(parts)[:MAX_CONTENT_LENGTH]


def _extract_doc(data: bytes) -> str:
    """Extract text from old .doc files (basic antiword approach)."""
    # .doc format is complex; try reading as text as fallback
    try:
        text = data.decode('utf-8', errors='ignore')
        # Filter out non-printable garbage
        import re
        clean = re.sub(r'[^\x20-\x7E一-鿿　-〿＀-￯\n\r\t]', '', text)
        return clean[:MAX_CONTENT_LENGTH]
    except Exception:
        return ''


def _extract_xls(data: bytes) -> str:
    """Extract text from old .xls files using xlrd if available."""
    try:
        import xlrd
        wb = xlrd.open_workbook(file_contents=data)
        parts = []
        for sheet in wb.sheets():
            parts.append(f'[Sheet: {sheet.name}]')
            for row_idx in range(sheet.nrows):
                row_text = ' | '.join(str(sheet.cell_value(row_idx, c)) for c in range(sheet.ncols) if sheet.cell_value(row_idx, c))
                if row_text.strip():
                    parts.append(row_text)
            if len('\n'.join(parts)) > MAX_CONTENT_LENGTH:
                break
        return '\n'.join(parts)[:MAX_CONTENT_LENGTH]
    except ImportError:
        return ''  # xlrd not installed
    except Exception:
        return ''


def _extract_xlsx(data: bytes) -> str:
    """Extract text from Excel files, row by row."""
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    parts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        parts.append(f'[Sheet: {sheet_name}]')
        for row in ws.iter_rows(values_only=True):
            row_text = ' | '.join(str(c) for c in row if c is not None)
            if row_text.strip():
                parts.append(row_text)
        if len('\n'.join(parts)) > MAX_CONTENT_LENGTH:
            break
    wb.close()
    return '\n'.join(parts)[:MAX_CONTENT_LENGTH]


def _extract_text(data: bytes) -> str:
    """Extract text from plain text files."""
    try:
        return data.decode('utf-8')[:MAX_CONTENT_LENGTH]
    except UnicodeDecodeError:
        try:
            return data.decode('gbk')[:MAX_CONTENT_LENGTH]
        except Exception:
            return ''
