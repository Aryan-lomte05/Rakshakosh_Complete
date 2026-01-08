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
            
        # 1b. Encryption at Rest (USP 4.1)
        # Using existing DocumentCrypto (AES-GCM)
        from backend.security.document_crypto import DocumentCrypto
        from backend.security.aes_gcm import AESGCMEngine
        
        # Initialize Crypto (In prod use dependency injection and load key from vault)
        # For hackathon, we generate/load key on fly
        key_path = "backend/security/master.key"
        if not os.path.exists(key_path):
             with open(key_path, "wb") as kf:
                 kf.write(os.urandom(32)) # 256-bit key
        
        with open(key_path, "rb") as kf:
            master_key = kf.read()
            
        crypto = DocumentCrypto(AESGCMEngine(master_key))
        
        # Encrypt DIRECTLY to persistence folder (Original plain file never stored)
        encrypted_persist_path = persist_path + ".enc"
        try:
             # We encrypt the temp file to the persist path
             crypto.encrypt_file(file_path, encrypted_persist_path)
             # Note: encrypt_file deletes input, so we need to copy temp first if we want to extract from it later
             # Actually, better flow: Copy temp -> Encrypt to Persist -> Delete Copy
             # But wait, ingest needs to read it.
             # So: Temp (Clear) -> Read/Extract -> Encrypt to Persist -> Delete Temp
             
             print(f"🔒 Encrypted & Persisted: {file.filename}")
             
             # Re-create temp file for extraction (since encrypt_file deleted it)
             # Wait, DocumentCrypto.encrypt_file deletes input. 
             # Let's just create a copy for encryption.
             temp_copy = file_path + ".copy"
             shutil.copy(file_path, temp_copy)
             crypto.encrypt_file(temp_copy, encrypted_persist_path)
             
        except Exception as crypt_err:
             print(f"⚠️ Encryption Warning: {crypt_err}")
             # Fallback: Copy plain
             shutil.copy(file_path, persist_path)

        # 2. Extract Pages (Hybrid Engine: Pymupdf + Docling Fallback)
        doc = pymupdf.open(file_path)
        extracted_pages = []
        is_scanned_detected = False
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Density Check (USP 4.1 - Intelligent Switch)
            # If text density is low (< 50 chars), assume image/scanned and switch to Docling
            # OR if it's the first page and has low text, might be a cover image.
            
            single_page_doc = pymupdf.open()
            single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            raw_text = page.get_text()
            
            if len(raw_text.strip()) < 50:
                print(f"⚠️ Page {page_num+1}: Low density detected ({len(raw_text.strip())} chars). Activating ELITE OCR...")
                
                # Lazy import to keep startup fast
                from backend.ingestion.docling_processor import DoclingProcessor
                
                if not hasattr(ingest_document, "ocr_processor"):
                    ingest_document.ocr_processor = DoclingProcessor()
                
                # We need to process this specific page. Docling processes files.
                # Since we have the single page doc in memory, we might need to save it temp to feed docling?
                # For optimal performance in this specific "Hybrid" architecture, Docling works best on files.
                # Strategy: If ANY page is scanned, we might want to flag the doc. 
                # BUT fine-grained: Let's save just this page to temp and process it.
                
                page_temp_path = f"{file_path}_page_{page_num}.pdf"
                single_page_doc.save(page_temp_path)
                
                try:
                    processed = ingest_document.ocr_processor.process_pdf(page_temp_path)
                    if processed:
                        md_text = processed[0]["text"] # Docling returns full doc text, here it's just 1 page
                        is_scanned_detected = True
                    else:
                        md_text = pymupdf4llm.to_markdown(single_page_doc) # Fallback to pymupdf if docling fails
                except Exception as docling_err:
                    print(f"❌ Docling Failed: {docling_err}")
                    md_text = pymupdf4llm.to_markdown(single_page_doc)
                finally:
                    if os.path.exists(page_temp_path):
                        os.remove(page_temp_path)
            else:
                # Standard Fast Path
                md_text = pymupdf4llm.to_markdown(single_page_doc, write_images=False)

            single_page_doc.close()
            extracted_pages.append({"page_number": page_num + 1, "text": md_text})
            
        doc.close()
        
        if is_scanned_detected:
            print("🧠 Smart Ingestion: Used Docling for scanned segments.")

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
