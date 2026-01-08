from backend.ingestion.text_extraction import extract_pdf_llm_blocks

PDF_PATH = "C:\\Users\\Aryan\\Downloads\\DeepCytes_Offer (2).pdf"

result = extract_pdf_llm_blocks(
    pdf_path=PDF_PATH,
    doc_id="test_doc_001",
    doc_name="sample_document",
    password=None
)

print("Engine:", result["engine"])
print("Pages:", result["total_pages"])
print("Blocks extracted:", len(result["blocks"]))

# Preview first block
if result["blocks"]:
    b = result["blocks"][0]
    print("\n--- SAMPLE BLOCK ---")
    print("Type:", b["type"])
    print("Page:", b["page_num"])
    print(b["text"][:500])
