# ocr.py
import pytesseract
from PIL import Image, UnidentifiedImageError
import requests
from io import BytesIO
import os

# IMPORTANT: After you install Tesseract (Windows installer),
# set the exact path to the installed tesseract.exe if it's not on PATH.
# Uncomment and update the line below with the full path to tesseract.exe on your PC.
# Example Windows default: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_text_from_image_uri(image_url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resp = requests.get(image_url, headers=headers, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Image fetch failed, status={resp.status_code}, url={image_url}")
    ctype = resp.headers.get("content-type","")
    if not ctype.startswith("image"):
        raise RuntimeError(f"URL did not return an image. content-type={ctype} url={image_url}")
    try:
        img = Image.open(BytesIO(resp.content))
        img.load()
    except UnidentifiedImageError as e:
        raise RuntimeError("Pillow could not identify image file (maybe corrupted or not an image)") from e
    text = pytesseract.image_to_string(img)
    return text

def extract_text_from_bytes(image_bytes: bytes) -> str:
    try:
        img = Image.open(BytesIO(image_bytes))
        img.load()
    except UnidentifiedImageError as e:
        raise RuntimeError("Uploaded data is not a valid image") from e
    text = pytesseract.image_to_string(img)
    return text