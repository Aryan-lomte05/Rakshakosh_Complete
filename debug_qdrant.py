import qdrant_client
from qdrant_client import QdrantClient

# print(f"Qdrant Client Version: {qdrant_client.__version__}")
client = QdrantClient(url="http://localhost:6333")
print("Client methods:")
print([m for m in dir(client) if not m.startswith("_")])
