import requests
import json
from typing import Generator, Optional
from backend.utils.logger import RakshaLogger

class OllamaClient:
    """
    HTTP Client for Ollama API.
    Uses direct API calls instead of brittle subprocess/CLI wrappers.
    """

    def __init__(self, model_name: str = "phi3"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"
        self.clear_gpu_memory() # Attempt to free VRAM on init
        
    def clear_gpu_memory(self):
        """
        Force unload models to clear VRAM and fix 'fallback to CPU' issues.
        Sends keep_alive=0 request.
        """
        try:
            RakshaLogger.info("OllamaClient", "🧹 Attempting to clear GPU VRAM...")
            requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "keep_alive": 0
                },
                timeout=5
            )
            RakshaLogger.success("OllamaClient", "✨ GPU Memory Reset Signal Sent")
        except Exception as e:
            RakshaLogger.warning("OllamaClient", f"⚠️ Failed to reset GPU: {e}")

    def generate(self, prompt: str) -> str:
        """Blocking generation (non-streaming)"""
        try:
            RakshaLogger.debug("OllamaClient", "⏳ Sending blocking request...")
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # Increased to 120s for CPU
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.Timeout:
            RakshaLogger.error("OllamaClient", "⏰ Request timed out (120s)")
            return "Error: Timeout"
        except Exception as e:
            print(f"Ollama HTTP Error: {e}")
            return "Error: Unable to generate response."

    def stream(self, prompt: str) -> Generator[str, None, None]:
        """
        True streaming generator via HTTP.
        """
        RakshaLogger.info("OllamaClient", f"🌊 Starting HTTP Stream for model '{self.model_name}'...")
        
        try:
            with requests.post(
                self.api_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": True # Enable streaming
                },
                stream=True,
                timeout=120 # Increased to 120s for CPU start
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        try:
                            # Parse JSON chunk
                            chunk = json.loads(line.decode('utf-8'))
                            token = chunk.get("response", "")
                            
                            # Check for completion
                            if chunk.get("done", False):
                                break
                                
                            if token:
                                yield token
                                
                        except json.JSONDecodeError:
                            continue
                            
        except GeneratorExit:
            RakshaLogger.info("OllamaClient", "🛑 Stream interrupted by user (GeneratorExit)")
            # Context manager will close 'response', closing the socket.
            return
            
        except Exception as e:
            print(f"Ollama Streaming Exception: {e}")
            yield f"Error: Streaming failed ({str(e)})."

