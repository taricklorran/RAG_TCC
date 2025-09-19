from services.container import get_qdrant_service

# Instância do service
qdrant_service = get_qdrant_service()

def create_collection_controller(name: str, vector_size: int):
    created = qdrant_service.create_collection(name, vector_size)
    if created:
        return {"message": "Collection criada com sucesso", "success": True}
    return {"message": "Ocorreu um erro na criação da Collection", "success": False}

def list_collections_controller():
    collections = qdrant_service.list_collections()
    return {"collections": collections, "success": True}

def get_collection_controller(collection_name: str):
    response = qdrant_service.get_collection(collection_name)
    if response["collection"]:
        return {"collection": response["collection"], "success": True}
    return {"collection": None, "message": response["error"],"success": False}

def delete_collection_controller(name: str):
    deleted = qdrant_service.delete_collection(name)
    if deleted:
        return {"message": "Collection deletada com sucesso", "success": True}
    return {"message": "Collection não existe", "success": False}