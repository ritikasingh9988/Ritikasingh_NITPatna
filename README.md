# Invoice Extractor - Datathon Submission

This project implements a simple invoice extraction API for the Bajaj Health Datathon.  
It extracts line items from invoice images (via URL or file upload) and returns JSON in the required format.


## 🚀 How to Run Locally

### 1. Create and activate virtual environment
```bash
python -m venv venv
.\venv\Scripts\activate     # Windows
# or
source venv/bin/activate   # Mac/Linux

2. Install dependencies

pip install -r requirements.txt

3. Run the API server

uvicorn main:app --host 0.0.0.0 --port 8000

4. Expose localhost using ngrok (for public access)

ngrok http 8000

Use the ngrok URL (https://xxxx.ngrok-free.dev) for submission.



📌 API Endpoints

POST /extract-bill-data

Extracts data from an image URL.

Request body:

{
  "document": "<image_url>"
}



POST /extract-bill-file

Upload an invoice file (JPG/PNG/PDF).

Form-data:

file: <upload file>



📄 Notes

Do NOT commit secret keys — keep them in .env

.env should be in .gitignore

For evaluation, keep both uvicorn server and ngrok running

Repository must have collaborator hackrxbot added (as per instructions)


📁 Project Structure

main.py
ocr.py
extractor.py
requirements.txt
.env (NOT included in GitHub)



📬 Contact / Help

If evaluation fails, restart:

1. uvicorn


2. ngrok


3. Test /docs again



This project is made specifically for the Datathon submission.
