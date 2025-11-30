# ocr.py
import io
import os
from PIL import Image, ImageFilter, ImageOps
import numpy as np
import pytesseract
from pdf2image import convert_from_bytes

# If Windows, set your tesseract path here (uncomment & edit if needed)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess_pil_image(img: Image.Image) -> Image.Image:
    """Basic preprocessing to improve OCR: grayscale, autocontrast, median filter, threshold."""
    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    # simple threshold - tuned for receipts
    img = img.point(lambda p: 255 if p > 170 else 0)
    return img

def ocr_image_bytes(img_bytes: bytes, tesseract_config: str = "--psm 6") -> str:
    """OCR one image from bytes using pytesseract."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    pre = preprocess_pil_image(img)
    text = pytesseract.image_to_string(pre, lang="eng", config=tesseract_config)
    return text

def pdf_bytes_to_pages_text(content: bytes, dpi: int = 300):
    """
    Try to extract text from PDF pages:
     - First try pdfplumber (in user code path; that is used in extractor)
     - If calling this fallback directly, rasterize pages with pdf2image and OCR them.
    """
    # Convert to images (pdf2image); use POPPLER_PATH env var if set
    poppler_path = os.environ.get("POPPLER_PATH", None)
    if poppler_path:
        images = convert_from_bytes(content, dpi=dpi, poppler_path=poppler_path)
    else:
        images = convert_from_bytes(content, dpi=dpi)
    pages_text = []
    for img in images:
        # convert PIL image to bytes for OCR helper
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        pages_text.append(ocr_image_bytes(buf.getvalue()))
    return pages_text