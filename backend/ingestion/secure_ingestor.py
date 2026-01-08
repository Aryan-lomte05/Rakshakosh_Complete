import io
import uuid
import hashlib
from datetime import datetime
from typing import List, Dict

from backend.security.password_vault import PasswordVault
from backend.security.document_crypto import decrypt_file_to_bytes
from backend.ingestion.text_extraction import extract_pdf_llm_blocks


class SecureIngestor:
    """
    Orchestrates secure ingestion of encrypted documents.
    Zero-trust. Air-gapped. Auditable.
    """

    def __init__(self, vault: PasswordVault):
        self.vault = vault

    # ---------- Core API ----------

    def ingest(
        self,
        encrypted_path: str,
        doc_id: str,
        doc_name: str,
        pipeline_stage: str = "fast"
    ) -> List[Dict]:
        """
        Main ingestion entrypoint.
        """

        # 1. Fetch document password
        doc_password = self.vault.retrieve_password(doc_id)

        # 2. Decrypt document into memory
        decrypted_bytes = decrypt_file_to_bytes(encrypted_path)

        try:
            # 3. Extract layout-aware blocks
            extraction = extract_pdf_llm_blocks(
                pdf_path=io.BytesIO(decrypted_bytes),
                doc_id=doc_id,
                doc_name=doc_name,
                password=doc_password
            )

            # 4. Convert blocks → chunks
            chunks = self._build_chunks(
                extraction=extraction,
                pipeline_stage=pipeline_stage
            )

            return chunks

        finally:
            # 5. Zeroize memory
            self._secure_wipe(decrypted_bytes)

    # ---------- Internal ----------

    def _build_chunks(
        self,
        extraction: Dict,
        pipeline_stage: str
    ) -> List[Dict]:
        """
        Converts extracted blocks into canonical Chunk schema.
        """

        blocks = extraction["blocks"]
        chunks: List[Dict] = []

        for idx, block in enumerate(blocks):
            chunk_id = f"{extraction['doc_id']}::{idx}"

            chunk = {
                # Identity
                "doc_id": extraction["doc_id"],
                "doc_name": extraction["doc_name"],
                "doc_version": self._doc_version(extraction),
                "chunk_id": chunk_id,

                # Ordering
                "chunk_index": idx,
                "prev_chunk_id": f"{extraction['doc_id']}::{idx-1}" if idx > 0 else None,
                "next_chunk_id": f"{extraction['doc_id']}::{idx+1}" if idx < len(blocks)-1 else None,

                # Provenance
                "page_start": block["page_num"],
                "page_end": block["page_num"],
                "section_path": "UNKNOWN",
                "char_start": -1,
                "char_end": -1,

                # Content
                "chunk_type": block["type"],
                "text": block["text"],
                "element_id": block.get("block_id"),
                "caption_text": None,
                "linked_chunk_ids": [],

                # Retrieval metadata (filled later)
                "token_count": len(block["text"].split()),
                "embedding_model": None,
                "vector_dim": None,

                # Pipeline
                "extraction_engine": extraction["engine"],
                "ingested_at": datetime.utcnow().isoformat(),
                "pipeline_stage": pipeline_stage,

                # Storage/security
                "text_storage": "encrypted_store"
            }

            chunks.append(chunk)

        return chunks

    # ---------- Helpers ----------

    def _doc_version(self, extraction: Dict) -> str:
        h = hashlib.sha256()
        h.update(f"{extraction['doc_id']}::{extraction['engine']}".encode())
        return h.hexdigest()[:16]

    def _secure_wipe(self, data: bytearray | bytes):
        """
        Best-effort memory wipe.
        """
        if isinstance(data, bytearray):
            for i in range(len(data)):
                data[i] = 0
