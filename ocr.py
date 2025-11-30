# ocr.py
import io
import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
import re

# If tesseract is not in PATH on Windows, set path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def clean_text(t: str) -> str:
    if t is None:
        return ""
    # normalize spaces and weird unicode
    t = t.replace('\r', '\n')
    t = re.sub(r'\n\s+\n', '\n', t)
    t = re.sub(r'[ \t]+', ' ', t)
    t = t.strip()
    return t

def extract_text_from_pdf_bytes(pdf_bytes: bytes, dpi: int = 200) -> list:
    """
    Return list of page texts (page index 0 -> page 1). If pdfplumber returns empty,
    fallback to image OCR for those pages.
    """
    pages_text = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(clean_text(text))
    except Exception:
        # if pdfplumber fails completely, fallback to image OCR for all pages
        pages_text = []

    # If any page is empty -> try OCR for that page using pdf2image
    need_ocr_idx = [i for i,t in enumerate(pages_text) if t.strip() == ""] if pages_text else None

    if pages_text == []:
        # do OCR for all pages
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        pages_text = []
        for img in images:
            try:
                txt = pytesseract.image_to_string(img)
            except Exception:
                txt = ""
            pages_text.append(clean_text(txt))
    elif need_ocr_idx:
        # render only needed pages to save time
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        for i in need_ocr_idx:
            try:
                txt = pytesseract.image_to_string(images[i])
            except Exception:
                txt = ""
            pages_text[i] = clean_text(txt)

    # ensure length equals num pages (if mismatch, pad)
    return [clean_text(t) for t in pages_text]