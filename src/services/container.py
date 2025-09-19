import os
from functools import lru_cache

from dotenv import load_dotenv

from config.qdrant import qdrant_client

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME")

@lru_cache()
def get_qdrant_service():
    from services.vectorstore.qdrant_service import QdrantService
    return QdrantService(client=qdrant_client)

@lru_cache()
def get_chunk_service():
    from services.chunking.chunk_service import ChunkerService
    return ChunkerService()

@lru_cache()
def get_embedder_service():
    from services.embedding.embedder_service import EmbedderService
    return EmbedderService(MODEL_NAME)

@lru_cache()
def get_metadata_service():
    from services.database.metadata_service import MetadataService
    return MetadataService()