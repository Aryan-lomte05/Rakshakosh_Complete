from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Added CORS
from datetime import datetime
import os
import sys
import json

# Add backend to path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
sys.path.append(root_dir)

from backend.api.agent_api import router as agent_router # Import agent router
from backend.api.ingestion_api import router as ingestion_router # Import ingestion router

# --------------------------------------------------
# App init
# --------------------------------------------------

app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router)
app.include_router(ingestion_router)
# --------------------------------------------------

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.json")

if not os.path.exists(CONFIG_PATH):
    raise RuntimeError(
        f"config.json not found at expected path: {CONFIG_PATH}"
    )

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# --------------------------------------------------
# Health endpoint
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "system": CONFIG["system"]["name"],
        "mode": CONFIG["system"]["mode"],
        "phase": CONFIG["system"]["phase"],
        "time_utc": datetime.utcnow().isoformat()
    }

@app.on_event("startup")
async def startup_event():
    """
    Startup persistence check:
    Scan backend/test_docs and ingest any missing files.
    """
    print("[Startup] 📥 Scanning backend/test_docs for persistence...")
    from backend.api.agent_api import agent
    from backend.ingestion.fast_ingestion import EnhancedPDFIngestion
    import hashlib
    import pymupdf
    import pymupdf4llm
    
    test_docs_dir = os.path.join(backend_dir, "test_docs")
    if not os.path.exists(test_docs_dir):
        os.makedirs(test_docs_dir)
        return

    # Get current index state
    try:
        existing_docs = agent.retriever.retriever.get_unique_documents()
        existing_set = set(existing_docs)
    except:
        existing_set = set()

    # Re-use ingestion engine (same settings as API)
    ingestion_engine = EnhancedPDFIngestion(collection_name="lollllll")
    
    count = 0
    for filename in os.listdir(test_docs_dir):
        if not filename.endswith(".pdf"):
            continue
            
        if filename in existing_set:
            continue
            
        # Needs ingestion
        print(f"[Startup] 🔄 Restoring: {filename}")
        file_path = os.path.join(test_docs_dir, filename)
        
        try:
             # Extract text (Using same logic as ingestion_api)
            doc = pymupdf.open(file_path)
            extracted_pages = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                single_page_doc = pymupdf.open()
                single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                md_text = pymupdf4llm.to_markdown(single_page_doc, write_images=False)
                single_page_doc.close()
                extracted_pages.append({"page_number": page_num + 1, "text": md_text})
            doc.close()

            full_content = "\n".join(p["text"] for p in extracted_pages)
            doc_id = hashlib.sha256(full_content.encode('utf-8')).hexdigest()[:16]

            ingestion_engine.ingest_for_retrieval(
                doc_id=doc_id,
                extracted_pages=extracted_pages,
                metadata={
                    "filename": filename,
                    "section_path": "Restored",
                    "pipeline_stage": "startup",
                    "text_storage": "plaintext"
                }
            )
            count += 1
        except Exception as e:
            print(f"[Startup] ❌ Failed to restore {filename}: {e}")

    if count > 0:
        print(f"[Startup] ✅ Restored {count} missing documents from persistence.")
        agent.retriever.retriever.reload_corpus()
    else:
        print("[Startup] ✨ All persistent documents are already indexed.")

# --------------------------------------------------
# Embedded server (DEPLOYMENT SAFE)
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,                      # <-- IMPORTANT FIX
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
