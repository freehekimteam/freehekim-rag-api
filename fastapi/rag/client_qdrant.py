from qdrant_client import QdrantClient
from config import Settings

settings = Settings()

_qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, api_key=settings.qdrant_api_key)

INTERNAL = "freehekim_internal"
EXTERNAL = "freehekim_external"

def search(vector, topk=5, collection=INTERNAL):
    return _qdrant.search(collection_name=collection, query_vector=vector, limit=topk)
