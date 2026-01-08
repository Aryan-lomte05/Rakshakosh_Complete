from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import hashlib
import pymupdf
import pymupdf4llm
from backend.ingestion.fast_ingestion import EnhancedPDFIngestion

router = APIRouter()

# Initialize Ingestion Engine (Lazy loading or singleton pattern recommended for prod)
# For now, we initialize on import but in a real app this should be a dependency
ingestion_engine = EnhancedPDFIngestion(
    collection_name="lollllll" # Matches current setup
)

TEMP_DIR = "backend/temp_ingest"
PERSIST_DIR = "backend/test_docs"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(PERSIST_DIR, exist_ok=True)

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingests a document (PDF) into the RAG system.
    1. Save to temp & persistence.
    2. Extract text (Markdown).
    3. Generate chunks & embeddings.
    4. Index in Qdrant.
    5. Return stats.
    """
    file_path = os.path.join(TEMP_DIR, file.filename)
    persist_path = os.path.join(PERSIST_DIR, file.filename)
    
    try:
        # 1. Save File to Temp
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1b. Save Copy to Persistence (backend/test_docs)
        shutil.copy(file_path, persist_path)
        print(f"📥 Received file: {file.filename} (Persisted to {persist_path})")

        # 2. Extract Pages (Simplified for live demo)
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

        # 3. Generate Doc ID
        full_content = "\n".join(p["text"] for p in extracted_pages)
        doc_id = hashlib.sha256(full_content.encode('utf-8')).hexdigest()[:16]

        # 4. Ingest
        result = ingestion_engine.ingest_for_retrieval(
            doc_id=doc_id,
            extracted_pages=extracted_pages,
            metadata={
                "filename": file.filename,
                "section_path": "Uploads",
                "pipeline_stage": "live",
                "text_storage": "plaintext" # TODO: Hook up encryption later if needed
            }
        )

        # Cleanup
        os.remove(file_path)
        
        # 🔄 HOT-RELOAD: Refresh the retriever's BM25 corpus so new docs are searchable immediately
        try:
            from backend.api.agent_api import agent
            agent.retriever.retriever.reload_corpus()
            print("🔄 Hot-reload triggered successfully!")
        except Exception as reload_error:
            print(f"⚠️ Hot-reload failed (restart may be needed): {reload_error}")

        return JSONResponse(content={
            "status": "success",
            "doc_id": doc_id,
            "filename": file.filename,
            "chunks": result["chunks_created"],
            "message": f"Successfully ingested {file.filename} ({result['chunks_created']} chunks)"
        })

    except Exception as e:
        print(f"❌ Ingestion Error: {str(e)}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))
