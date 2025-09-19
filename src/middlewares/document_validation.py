from fastapi import HTTPException

from services.container import get_qdrant_service, get_metadata_service
from services.vectorstore.qdrant_service import QdrantService

# Instância do service
qdrant_service = get_qdrant_service()
metadata_service = get_metadata_service()

class DcoumentValidation:
    @staticmethod
    def document_id_not_empty(doc_id: str):
        if not doc_id:
            raise HTTPException(status_code=400, detail={"message": "ID do documento não pode ser vazio", "success": False})
    
    @staticmethod
    def document_extension(file_name: str):
        if not file_name.endswith(('.pdf', '.txt', '.docx')):
            raise HTTPException(status_code=400, detail={"message": "Formato de arquivo inválido", "success": False})

    @staticmethod
    def document_exists(doc_hash: str, collection_name: str):
        if qdrant_service.document_exists(doc_hash, collection_name):
            raise HTTPException(status_code=400, detail={"message": "Documento já existe na base", "success": False})
        
    @staticmethod
    def document_not_exists(doc_hash: str, collection_name: str):
        if not qdrant_service.document_exists(doc_hash, collection_name):
            raise HTTPException(status_code=400, detail={"message": "Documento não existe na base", "success": False})
        
    @staticmethod
    def document_id_exists(doc_id: str):
        if not metadata_service.get_document_by_id(doc_id):
            raise HTTPException(status_code=404, detail={"message": f"Documento com ID '{doc_id}' não encontrado", "success": False})
        
    @staticmethod
    def document_content_exists(collection_name: str, doc_hash: str):
        """Verifica no banco de metadados se um documento com o mesmo hash já foi registrado."""
        if metadata_service.get_document_by_hash(collection_name, doc_hash):
            raise HTTPException(
                status_code=409,
                detail={"message": "Um documento com este mesmo conteúdo já existe na coleção", "success": False}
            )