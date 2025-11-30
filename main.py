# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
import uvicorn
from ocr import extract_text_from_pdf_bytes
from extractor import run_full_extraction
import traceback

app = FastAPI(title="Invoice/Bill Extractor")

@app.post("/extract-bill-file")
async def extract_bill_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
        # get page texts
        pages = extract_text_from_pdf_bytes(content, dpi=200)
        # run extractors
        result = run_full_extraction(pages)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))

if __name__ == "__main__":
    # for local testing
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)