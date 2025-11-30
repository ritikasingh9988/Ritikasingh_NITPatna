# main.py
from fastapi import FastAPI, File, UploadFile
from typing import Any
import io, os, logging

from extractor import extract_bill_from_text_pages
from ocr import pdf_bytes_to_pages_text

app = FastAPI(title="Invoice Extractor (PDF+OCR)")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

@app.post("/extract-bill-file")
async def extract_bill_file(file: UploadFile = File(...)) -> Any:
    try:
        content = await file.read()
        # Try to extract text pages via pdfplumber first in user environment (handled inside pdf_bytes_to_pages_text fallback)
        pages_text = []
        # We'll try pdfplumber here — if not present, pdf_bytes_to_pages_text will rasterize and OCR
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for p in pdf.pages:
                    pages_text.append(p.extract_text() or "")
        except Exception:
            # fallback to image-based OCR using pdf2image + pytesseract
            pages_text = pdf_bytes_to_pages_text(content)
        pages = extract_bill_from_text_pages(pages_text)
        # compute reconciled amount
        total = 0.0
        for pg in pages:
            for it in pg["bill_items"]:
                try:
                    total += float(it.get("item_amount") or 0.0)
                except:
                    pass
        resp = {"is_success": True, "data": {"pagewise_line_items": pages, "total_item_count": sum(len(p["bill_items"]) for p in pages), "reconciled_amount": round(total,2)}}
        return resp
    except Exception as e:
        logger.exception("extract error")
        return {"is_success": False, "error": str(e)}