
import sys
import time
from backend.ai_model.llm.ollama_client import OllamaClient

def test_streaming():
    print("Testing Ollama Streaming...")
    client = OllamaClient(model_name="phi3")
    prompt = "Explain scaled dot product attention in one sentence."
    
    print(f"Prompt: {prompt}")
    start = time.time()
    
    try:
        count = 0
        for token in client.stream(prompt):
            sys.stdout.write(token)
            sys.stdout.flush()
            count += 1
        
        print(f"\n\nDone. Tokens received: {count}")
        print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    test_streaming()
