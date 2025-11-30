# ocr.py
import io
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import re

# helper to clean text lines
def clean_text(t: str) -> str:
    if t is None:
        return ""
    # normalize whitespace and remove repeated newlines
    t = re.sub(r'\r\n', '\n', t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n{2,}', '\n', t)
    return t.strip()

def extract_text_from_pdf_bytes(pdf_bytes: bytes, dpi: int = 200) -> list:
    """
    Return list of page texts. Uses pdfplumber to get textual text; if page
    has no text (likely scanned) use pdf2image + pytesseract.
    """
    pages_text = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt and txt.strip():
                    pages_text.append(clean_text(txt))
                else:
                    # fallback: render page as image and OCR
                    try:
                        images = convert_from_bytes(pdf_bytes, dpi=dpi, first_page=page.page_number, last_page=page.page_number)
                        if images:
                            ocr_txt = pytesseract.image_to_string(images[0])
                            pages_text.append(clean_text(ocr_txt))
                        else:
                            pages_text.append("")
                    except Exception:
                        pages_text.append("")
    except Exception:
        # if pdfplumber fails for the whole file, fallback to images + OCR for all pages
        try:
            images = convert_from_bytes(pdf_bytes, dpi=dpi)
            for img in images:
                pages_text.append(clean_text(pytesseract.image_to_string(img)))
        except Exception:
            # ultimate fallback: empty pages
            pages_text = []
    # ensure at least empty strings per page if any missing
    if not pages_text:
        return []
    return pages_text