# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import traceback

from ocr import extract_text_from_pdf_bytes
from extractor_module import find_items_from_page_text, find_totals_and_reconcile, parse_amount

app = FastAPI(title="Bill / Invoice Extractor")

@app.post("/extract-bill-file")
async def extract_bill_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        pages = extract_text_from_pdf_bytes(content)
        if not pages:
            # return empty structure but success false might be considered
            return JSONResponse({"is_success": True, "data": {"pagewise_line_items": [], "total_item_count": 0, "reconciled_amount": 0.0, "grand_total_found": 0.0}})
        pagewise = []
        all_items = []
        for idx, ptxt in enumerate(pages):
            items = find_items_from_page_text(ptxt)
            page_entry = {
                "page_no": idx+1,
                "page_type": "Bill Detail",
                "bill_items": items
            }
            pagewise.append(page_entry)
            all_items.extend(items)
        total_extracted = sum(i.get('item_amount', 0.0) or 0.0 for i in all_items)
        grand, _ = find_totals_and_reconcile(pages)
        reconciled = 0.0
        if grand is not None:
            reconciled = round(grand - round(total_extracted, 2), 2)
        response = {
            "is_success": True,
            "data": {
                "pagewise_line_items": pagewise,
                "total_item_count": len(all_items),
                "reconciled_amount": reconciled,
                "grand_total_found": grand if grand is not None else 0.0
            }
        }
        return JSONResponse(response)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)