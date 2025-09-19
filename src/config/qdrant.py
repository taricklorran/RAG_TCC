import os

from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL")

# conexão com o Qdrant

qdrant_client = QdrantClient(url=QDRANT_URL)