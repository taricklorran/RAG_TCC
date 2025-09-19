from fastapi import HTTPException

from services.container import get_qdrant_service
from services.vectorstore.qdrant_service import QdrantService

# Instância do service
qdrant_service = get_qdrant_service()

class CollectionValidation:
    @staticmethod
    def collection_name_not_empty(collection_name: str):
        if not collection_name:
            raise HTTPException(status_code=400, detail={"message": "Nome da coleção não pode ser vazio", "success": False})
    
    @staticmethod
    def collection_exists(collection_name: str):
        if not qdrant_service.collection_exists(collection_name):
            raise HTTPException(status_code=404, detail={"message": "Collection não existe", "success": False})
        
    @staticmethod
    def collection_does_not_exist(collection_name: str):
        if qdrant_service.collection_exists(collection_name):
            raise HTTPException(status_code=400, detail={"message": "Collection não existe", "success": False})