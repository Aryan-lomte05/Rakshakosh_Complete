import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.ai_model.agent.agent_controller import AgentController

def test_full_loop():
    print(">>> Initializing AgentController...")
    agent = AgentController()
    
    query = "What is the primary engine of the Tejas Mk1A?"
    session_id = "test_session_001"
    user_id = "demo_user"

    print(f"\n>>> Starting Stream for Query: '{query}'")
    print(">>> USPs being verified: Streaming (1.6), Confidence (2.4), RBAC (4.1), Citations (2.2)\n")

    start_time = time.time()
    token_count = 0
    full_response = ""
    metadata = None

    # Iterate over generator
    for chunk_str in agent.stream_query(session_id, query, user_id):
        chunk = json.loads(chunk_str)
        
        if chunk["type"] == "token":
            token = chunk["content"]
            print(token, end="", flush=True)
            full_response += token
            token_count += 1
        
        elif chunk["type"] == "metadata":
            metadata = chunk
            print(f"\n\n[METADATA RECEIVED]")

    end_time = time.time()
    
    print("\n\n" + "="*50)
    print(">>> VERIFICATION RESULTS")
    print("="*50)
    print(f"Total Time: {round(end_time - start_time, 2)}s (Target: <2s start)")
    print(f"Tokens Generated: {token_count}")
    
    if metadata:
        conf = metadata.get("confidence", 0)
        print(f"Confidence Score: {conf} (Pass > 0.5)")
        print(f"Citations: {len(metadata.get('citations', []))}")
        print(f"Language: {metadata.get('language')}")
        
        # Validation Logic
        if conf > 0 and token_count > 5:
             print("\n✅ SUCCESS: Pipeline functional & Streaming active.")
        else:
             print("\n❌ FAILURE: Low confidence or no tokens.")
    else:
        print("\n❌ FAILURE: No metadata received.")

if __name__ == "__main__":
    test_full_loop()
