from qdrant_client import QdrantClient
from config import Settings

settings = Settings()

# Use HTTPS only for port 443 (production), HTTP for local development
use_https = settings.qdrant_port == 443
_qdrant = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    api_key=settings.qdrant_api_key,
    https=use_https
)

INTERNAL = "freehekim_internal"
EXTERNAL = "freehekim_external"

def search(vector, topk=5, collection=INTERNAL):
    return _qdrant.search(collection_name=collection, query_vector=vector, limit=topk)
