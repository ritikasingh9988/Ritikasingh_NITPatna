# ocr.py
import pytesseract
from PIL import Image
import io

def image_bytes_to_text(image_bytes: bytes) -> str:
    img = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(img)