#!/usr/bin/env python3
"""
SIMPLE TEST - Just run this file
Ingests your 3 PDFs into Qdrant Docker
"""

import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any

import pymupdf
import pymupdf4llm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class EnhancedPDFIngestion:
    """Enhanced PDF Ingestion"""
    
    def __init__(self,
                 embed_model: str = "BAAI/bge-base-en-v1.5",
                 qdrant_url: str = "http://localhost:6333",
                 collection_name: str = "lollllll"):  # FIXED: Must match interactive_retriever.py
        
        self.embed_model_name = embed_model
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        
        print(f"Loading embedding model...")
        self.embed_model = SentenceTransformer(embed_model)
        self.vector_size = self.embed_model.get_sentence_embedding_dimension()
        
        print(f"Connecting to Qdrant...")
        self.client = QdrantClient(url=qdrant_url)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=150,
            separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""],
            length_function=len
        )
        print(f"✅ Ready!\n")
    def _generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        # Generate deterministic UUID based on content-derived doc_id
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_chunk_{chunk_index:04d}"))
    
    def _is_table(self, text: str) -> bool:
        lines = text.strip().split('\n')
        has_pipes = sum(1 for line in lines if '|' in line and line.count('|') >= 2)
        has_separator = any('|---' in line or '| ---' in line for line in lines)
        return has_pipes >= 2 and has_separator
    
    def chunk_pages_enhanced(self, 
                            pages: List[Dict[str, Any]], 
                            doc_id: str,
                            doc_name: str,
                            doc_version: str,
                            metadata: dict) -> List[Dict[str, Any]]:
        
        all_chunks = []
        chunk_index = 0
        char_offset = 0
        ingested_at = datetime.utcnow().isoformat() + "Z"
        
        for page in pages:
            text = page["text"].strip()
            if not text:
                continue
            
            page_num = page.get("page_number", page.get("page_num", 1))
            
            if self._is_table(text):
                chunk_id = self._generate_chunk_id(doc_id, chunk_index)
                
                chunk = {
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "doc_version": doc_version,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "prev_chunk_id": self._generate_chunk_id(doc_id, chunk_index - 1) if chunk_index > 0 else None,
                    "next_chunk_id": None,
                    "page_start": page_num,
                    "page_end": page_num,
                    "section_path": metadata.get("section_path", ""),
                    "char_start": char_offset,
                    "char_end": char_offset + len(text),
                    "chunk_type": "table",
                    "text": text,
                    "element_id": f"{doc_id}_table_{chunk_index}",
                    "caption_text": None,
                    "linked_chunk_ids": [],
                    "token_count": len(text.split()),
                    "embedding_model": self.embed_model_name,
                    "vector_dim": self.vector_size,
                    "extraction_engine": "pymupdf4llm",
                    "ingested_at": ingested_at,
                    "pipeline_stage": metadata.get("pipeline_stage", "fast"),
                    "text_storage": metadata.get("text_storage", "plaintext"),
                }
                
                all_chunks.append(chunk)
                char_offset += len(text) + 2
                chunk_index += 1
                
            else:
                text_chunks = self.text_splitter.split_text(text)
                
                for chunk_text in text_chunks:
                    chunk_id = self._generate_chunk_id(doc_id, chunk_index)
                    
                    chunk = {
                        "doc_id": doc_id,
                        "doc_name": doc_name,
                        "doc_version": doc_version,
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index,
                        "prev_chunk_id": self._generate_chunk_id(doc_id, chunk_index - 1) if chunk_index > 0 else None,
                        "next_chunk_id": None,
                        "page_start": page_num,
                        "page_end": page_num,
                        "section_path": metadata.get("section_path", ""),
                        "char_start": char_offset,
                        "char_end": char_offset + len(chunk_text),
                        "chunk_type": "prose",
                        "text": chunk_text,
                        "element_id": None,
                        "caption_text": None,
                        "linked_chunk_ids": [],
                        "token_count": len(chunk_text.split()),
                        "embedding_model": self.embed_model_name,
                        "vector_dim": self.vector_size,
                        "extraction_engine": "pymupdf4llm",
                        "ingested_at": ingested_at,
                        "pipeline_stage": metadata.get("pipeline_stage", "fast"),
                        "text_storage": metadata.get("text_storage", "plaintext"),
                    }
                    
                    # 🔍 INGESTION LOGGING (User Request)
                    print(f"\n[INGEST CHUNK {chunk_index}] Doc: {doc_name} | Page: {page_num}")
                    print(f"--- START TEXT ---")
                    print(chunk_text[:300] + "..." if len(chunk_text) > 300 else chunk_text)
                    print(f"--- END TEXT ---\n")
                    
                    all_chunks.append(chunk)
                    char_offset += len(chunk_text) + 2
                    chunk_index += 1
        
        for i in range(len(all_chunks) - 1):
            all_chunks[i]["next_chunk_id"] = all_chunks[i + 1]["chunk_id"]
        
        return all_chunks
    
    def add_contextual_prefix(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for chunk in chunks:
            chunk["contextual_text"] = (
                f"[Doc: {chunk['doc_name']}][Page: {chunk['page_start']}]\n"
                f"{chunk['text']}"
            )
        return chunks
    
    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32) -> List[Dict[str, Any]]:
        print(f"Embedding {len(chunks)} chunks...")
        texts = [chunk["contextual_text"] for chunk in chunks]
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.embed_model.encode(
                batch,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            embeddings.extend(batch_embeddings.tolist())
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        
        return chunks
    
    def create_collection(self, recreate: bool = False):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if exists and not recreate:
            return
        
        if exists and recreate:
            self.client.delete_collection(self.collection_name)
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE
            )
        )
    
    def upload_to_qdrant(self, chunks: List[Dict[str, Any]], batch_size: int = 100):
        print(f"Uploading to Qdrant...")
        points = []
        
        for chunk in chunks:
            payload = {k: v for k, v in chunk.items() if k != "embedding"}
            
            point = PointStruct(
                id=chunk["chunk_id"],
                vector=chunk["embedding"],
                payload=payload
            )
            points.append(point)
        
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
    
    def ingest_for_retrieval(self,
                            doc_id: str,
                            extracted_pages: List[Dict],
                            metadata: Dict) -> Dict:
        """
        Fast ingestion path
        """
        doc_name = metadata.get("filename", metadata.get("doc_name", "unknown"))
        
        full_text = "\n".join(p["text"] for p in extracted_pages if p.get("text"))
        doc_version = hashlib.sha256(full_text.encode('utf-8')).hexdigest()[:16]
        
        chunks = self.chunk_pages_enhanced(
            pages=extracted_pages,
            doc_id=doc_id,
            doc_name=doc_name,
            doc_version=doc_version,
            metadata=metadata
        )
        
        chunks = self.add_contextual_prefix(chunks)
        chunks = self.embed_chunks(chunks)
        
        self.create_collection(recreate=False)
        self.upload_to_qdrant(chunks)
        
        return {
            "doc_id": doc_id,
            "chunks_created": len(chunks),
            "collection": self.collection_name,
            "mode": "fast"
        }


# ============================================================================
# SIMPLE TEST - JUST RUN THIS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 SIMPLE INGESTION TEST")
    print("="*70 + "\n")
    
    # 1. Initialize
    ingestion = EnhancedPDFIngestion(
        embed_model="BAAI/bge-base-en-v1.5",
        qdrant_url="http://localhost:6333",
        collection_name="lollllll"
    )
    
    # 2. Your PDF paths
    pdf_paths = [
        "C:/Users/Aryan/OneDrive/Desktop/RAKSHAKOSH_LOCAL/backend/test_docs/1810.04805v2.pdf",
        "C:/Users/Aryan/OneDrive/Desktop/RAKSHAKOSH_LOCAL/backend/test_docs/2008.11015v4.pdf",
        "C:/Users/Aryan/OneDrive/Desktop/RAKSHAKOSH_LOCAL/backend/test_docs/NIPS-2017-attention-is-all-you-need-Paper.pdf"
    ]
    
    doc_names = ["transformer_paper", "bert_paper", "table2charts_paper"]
    
    # 3. Process each PDF
    for pdf_path, doc_name in zip(pdf_paths, doc_names):
        print(f"\n📄 Processing: {doc_name}")
        print("-" * 70)
        
        # Extract pages
        print("Extracting...")
        doc = pymupdf.open(pdf_path)
        extracted_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            # Extract markdown for THIS page only by creating single-page doc
            single_page_doc = pymupdf.open()
            single_page_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            md_text = pymupdf4llm.to_markdown(single_page_doc, write_images=False)
            single_page_doc.close()
            
            extracted_pages.append({"page_number": page_num + 1, "text": md_text})
        
        doc.close()
        print(f"✅ Extracted {len(extracted_pages)} pages")
        
        # Generate doc_id
        full_content = "\n".join(p["text"] for p in extracted_pages)
        doc_id = hashlib.sha256(full_content.encode('utf-8')).hexdigest()[:16]
        
        # Ingest
        result = ingestion.ingest_for_retrieval(
            doc_id=doc_id,
            extracted_pages=extracted_pages,
            metadata={
                "filename": f"{doc_name}.pdf",
                "section_path": f"Papers > {doc_name}",
                "pipeline_stage": "fast",
                "text_storage": "plaintext"
            }
        )
        
        print(f"✅ Result: {result}\n")
    
    print("="*70)
    print("✅ ALL DONE!")
    print("🎯 Check Qdrant: http://localhost:6333/dashboard")
    print("="*70 + "\n")