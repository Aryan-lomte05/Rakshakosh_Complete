
import sys
import time
import subprocess
from backend.ai_model.llm.ollama_client import OllamaClient

def test_large_prompt():
    print("Testing Ollama with LARGE prompt (4000+ chars)...")
    
    # Generate large dummy context
    large_context = "This is a dummy sentence to fill up space. " * 200
    prompt = f"Context:\n{large_context}\n\nQuestion: What is the context about?"
    
    print(f"Prompt length: {len(prompt)} chars")
    
    client = OllamaClient(model_name="phi3")
    
    start = time.time()
    count = 0
    try:
        # We manually use the internal logic to debug deeply if needed, 
        # but let's trust the class first.
        for token in client.stream(prompt):
            sys.stdout.write(token)
            sys.stdout.flush()
            count += 1
            
        print(f"\n\nDone. Tokens received: {count}")
        print(f"Time taken: {time.time() - start:.2f}s")
        
        if count == 0:
            print("❌ FAILURE: No tokens received.")
            
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_large_prompt()
