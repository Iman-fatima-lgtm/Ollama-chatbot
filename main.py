from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from docx import Document
from uuid import uuid4
import shutil, os, io, requests

from database import SessionLocal, engine
from models import DocumentEntry
from database import Base

app = FastAPI()
Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        file_stream = io.BytesIO(file_bytes)
        document = Document(file_stream)
        return "\n".join([p.text for p in document.paragraphs if p.text.strip()])
    except Exception as e:
        raise RuntimeError("Could not read DOCX: " + str(e))

@app.post("/upload/")
async def upload_doc(
    user_id: str = Form(...),
    website_name: str = Form(...),
    website_url: str = Form(...),
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")
    
    unique_id = str(uuid4())
    saved_path = os.path.join(UPLOAD_DIR, f"{unique_id}.docx")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    db = SessionLocal()
    entry = DocumentEntry(
        user_id=user_id,
        website_name=website_name,
        website_url=website_url,
        file_path=saved_path,
        unique_endpoint=unique_id
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    db.close()
    
    return {"message": "Document uploaded", "chatbot_endpoint": f"/chat/{unique_id}"}

@app.post("/chat/{doc_id}")
async def chat_with_uploaded_doc(doc_id: str, question: str = Form(...)):
    db = SessionLocal()
    entry = db.query(DocumentEntry).filter(DocumentEntry.unique_endpoint == doc_id).first()
    db.close()

    if not entry:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    with open(entry.file_path, "rb") as f:
        doc_bytes = f.read()
    
    doc_content = extract_text_from_docx(doc_bytes)
    full_prompt = f"""You are an assistant that answers questions based only on the following document:\n\n{doc_content}\n\nQuestion: {question}\nAnswer:"""

    try:
        response = requests.post(OLLAMA_API_URL, json={
            "model": "gemma:2b",
            "prompt": full_prompt,
            "stream": False
        })
        response.raise_for_status()
        return {"response": response.json()["response"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
