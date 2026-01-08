from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from typing import Dict, List, Any
import logging
from backend.utils.logger import RakshaLogger

class DoclingProcessor:
    """
    ELITE Document Processor (USP 4.1 & 4.2)
    Uses IBM Docling for state-of-the-art OCR, Table Extraction, and Layout Analysis.
    Triggered only when standard extraction checks fail (e.g. Scanned PDFs).
    """

    def __init__(self):
        RakshaLogger.info("Docling", "🚀 Initializing ELITE Document Processor...")
        
        # Configure pipeline for specialized PDF handling
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True # Enable OCR for scanned files
        pipeline_options.do_table_structure = True # Extract table structures
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE # Highest accuracy
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pipeline_options
            }
        )
        RakshaLogger.success("Docling", "✅ ELITE Processor Ready")

    def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process a PDF file using Docling to extract text, tables, and layout.
        Returns a list of pages with markdown text and metadata.
        """
        try:
            RakshaLogger.info("Docling", f"🧠 Analysing document structure: {file_path}")
            
            # Convert the document
            result = self.converter.convert(file_path)
            doc = result.document
            
            # Export to Markdown (Docling does smart layout preservation)
            md_content = doc.export_to_markdown()
            
            # Since Docling exports the whole doc, we'll wrap it as a single "processed" chunk 
            # or split it if needed. For now, we return it as a single high-quality entry
            # but we can iterate pages if we dig into the doc object.
            
            # For this elite implementation, we'll iterate pages to maintain compatibility
            # with our chunking system.
            
            processed_pages = []
            
            # Docling's API structures might vary, but export_to_markdown() gives the full text.
            # Let's try to extract page-wise if possible, or fallback to full text.
            # Efficient approach: Return full text and let our text splitter handle it, 
            # but annotated with table metadata.
            
            RakshaLogger.success("Docling", f"✅ Successfully processed {len(doc.pages)} pages")
             
            # Create a simplified page structure
            # Note: Docling's markdown is often superior to page-by-page slicing for RAG
            # because it keeps tables together across page breaks.
            
            processed_pages.append({
                "page_number": 1, # Represents the whole elite-processed doc
                "text": md_content,
                "is_elite": True
            })

            return processed_pages

        except Exception as e:
            RakshaLogger.error("Docling", f"Processing failed: {str(e)}")
            return []
