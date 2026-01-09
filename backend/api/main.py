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
from backend.api.analytics_api import router as analytics_router # Import analytics router

# NEW: Auth and Documents routers
from backend.auth.auth_api import router as auth_router
from backend.documents.document_api import router as documents_router

# NEW: MongoDB
from backend.db.mongodb import Database, create_indexes

# --------------------------------------------------
# App init
# --------------------------------------------------

app = FastAPI(
    title="RakshaKosh API",
    description="Tier-Based RBAC Document Access System with RAG",
    version="2.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)        # NEW: /auth/*
app.include_router(documents_router)   # NEW: /documents/*
app.include_router(agent_router)
app.include_router(ingestion_router)
app.include_router(analytics_router)
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
async def health():
    """
    ELITE System Diagnostics (USP: Health Check Endpoint)
    Returns real-time hardware stats and component health.
    """
    import psutil
    
    # Hardware Stats
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=None)
    
    # Component Checks (Fast failures)
    vector_db_status = "unknown"
    try:
        if agent_router.agent.retriever:
            vector_db_status = "online"
    except:
        vector_db_status = "offline"

    return {
        "status": "ok",
        "system_info": {
            "name": CONFIG["system"]["name"],
            "version": "2.0.0 (Award-Winning)",
            "time_utc": datetime.utcnow().isoformat()
        },
        "hardware": {
            "cpu_usage_percent": cpu,
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_usage_percent": mem.percent,
            "ram_available_gb": round(mem.available / (1024**3), 2)
        },
        "components": {
            "vector_db": vector_db_status,
            "mode": CONFIG["system"]["mode"],
            "security_layer": "active"
        }
    }

# --------------------------------------------------
# MongoDB Lifecycle Events
# --------------------------------------------------

@app.on_event("startup")
async def startup_mongodb():
    """Connect to MongoDB and create indexes."""
    try:
        await Database.connect()
        await create_indexes()
        print("✅ MongoDB connected and indexes created")
    except Exception as e:
        print(f"⚠️ MongoDB connection failed: {e}")
        print("   Auth features will not work without MongoDB.")

@app.on_event("shutdown")
async def shutdown_mongodb():
    """Disconnect from MongoDB."""
    await Database.disconnect()

# --------------------------------------------------
# Existing Startup Event (Persistence Check)
# --------------------------------------------------

@app.on_event("startup")
async def startup_persistence_check():
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
