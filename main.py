from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
from extractor_module import run_full_extraction

app = FastAPI(title="Invoice / Bill Extractor")

@app.post("/extract-bill-file")
async def extract_bill_file(file: UploadFile = File(...)):
    try:
        body = await file.read()
        result = run_full_extraction(body)
        return JSONResponse(content=result)
    except Exception as e:
        # return 500 with message for debugging (you can remove message in production)
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    # run locally: python main.py
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)