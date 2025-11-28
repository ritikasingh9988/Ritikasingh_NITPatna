# main.py
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from typing import Any
from extractor import call_llm_for_items
from ocr import extract_text_from_bytes, extract_text_from_image_uri
import traceback
import os

app = FastAPI(title="Invoice Extractor")

class RequestBody(BaseModel):
    document: str

@app.post("/extract-bill-data")
def extract_bill_data(body: RequestBody):
    try:
        text = extract_text_from_image_uri(body.document)
        items = call_llm_for_items(text)
        total = sum([float(i.get("item_amount") or 0) for i in items])
        return {
            "is_success": True,
            "data": {
                "pagewise_line_items": [{"page_no": "1", "bill_items": items}],
                "total_item_count": len(items),
                "reconciled_amount": round(total,2)
            }
        }
    except Exception as e:
        return {"is_success": False, "error": str(e), "traceback": traceback.format_exc()}

@app.post("/extract-bill-file")
async def extract_bill_file(file: UploadFile = File(...)) -> Any:
    try:
        content = await file.read()
        text = extract_text_from_bytes(content)
        items = call_llm_for_items(text)
        total = sum([float(i.get("item_amount") or 0) for i in items])
        return {
            "is_success": True,
            "data": {
                "pagewise_line_items": [{"page_no": "1", "bill_items": items}],
                "total_item_count": len(items),
                "reconciled_amount": round(total,2)
            }
        }
    except Exception as e:
        return {"is_success": False, "error": str(e), "traceback": traceback.format_exc()}