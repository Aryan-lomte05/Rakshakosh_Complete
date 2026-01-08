
import requests
import json
import sys

def test_backend():
    url = "http://localhost:8000/chat/stream"
    payload = {
        "query": "What is scaled dot product attention",
        "session_id": "test_session_123",
        "user_id": "demo_user"
    }
    
    print(f"🌊 Connecting to {url}...")
    
    try:
        with requests.post(url, json=payload, stream=True) as response:
            if response.status_code != 200:
                print(f"❌ Error: {response.status_code} - {response.text}")
                return

            print("✅ Connected! Reading stream...")
            print("-" * 50)
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data["type"] == "token":
                            sys.stdout.write(data["content"])
                            sys.stdout.flush()
                        elif data["type"] == "metadata":
                            print(f"\n\n[METADATA] Confidence: {data['confidence']}")
                    except json.JSONDecodeError:
                        print(f"⚠️ JSON Error: {line}")
                        
        print("\n" + "-" * 50)
        print("✅ Stream finished.")
        
    except Exception as e:
        print(f"\n❌ Exception: {e}")

if __name__ == "__main__":
    test_backend()
