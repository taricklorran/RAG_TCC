# controllers/document_controller.py
import os
import uuid
from pathlib import Path
from bson.objectid import ObjectId
from services.container import (get_chunk_service, get_embedder_service,
                                get_qdrant_service, get_metadata_service)

# Instância dos services
qdrant_service = get_qdrant_service()
chunk_service = get_chunk_service()
embedder_service = get_embedder_service()
metadata_service = get_metadata_service()

def upload_document_controller(
    hash_document: str,
    file_content: bytes, 
    filename: str, 
    collection_name: str, 
    document_id_to_update: str | None = None,
    parent_document_id: str | None = None
):
    """
    Orquestra o upload, processamento e armazenamento do documento.
    """
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    temp_filepath = temp_dir / f"{uuid.uuid4()}_{filename}"
    with open(temp_filepath, "wb") as f:
        f.write(file_content)

    try:
        # Processa o novo arquivo para o Qdrant
        chunks = chunk_service.chunk_document(str(temp_filepath), doc_id=hash_document, filename=filename)
        if isinstance(chunks, dict):
            return chunks

        vectors = embedder_service.embed_chunks(chunks)

        print(f"\n\nVETORES:")
        print(f"{vectors}\n\n")

        qdrant_service.index_chunks(chunks, collection_name=collection_name, vectors=vectors)

        if document_id_to_update:
            # 1. Obter metadados da versão antiga
            old_metadata = metadata_service.get_document_by_id(document_id_to_update)
            if not old_metadata:
                 return {"message": f"Documento com ID {document_id_to_update} não encontrado para atualização.", "success": False}
            old_hash = old_metadata['active_version_hash']
            old_gridfs_file_id = old_metadata.get('gridfs_file_id')

            qdrant_service.delete_by_doc_id(old_hash, collection_name)
            
            new_gridfs_file_id = metadata_service.save_file(file_content, filename, hash_document)

            metadata_service.update_document_version(document_id_to_update, hash_document, filename, new_gridfs_file_id)

            if old_gridfs_file_id:
                # Verifica se algum OUTRO documento ainda usa o arquivo antigo
                other_references = metadata_service.collection.count_documents({
                    "gridfs_file_id": old_gridfs_file_id,
                    "_id": {"$ne": ObjectId(document_id_to_update)}
                })

                if other_references == 0:
                    print(f"INFO: Nenhuma outra referência encontrada para o arquivo antigo. Excluindo do GridFS.")
                    metadata_service.delete_file_from_gridfs(old_gridfs_file_id)
                else:
                    print(f"INFO: O arquivo antigo ainda é referenciado por {other_references} outro(s) documento(s). Não será excluído do GridFS.")
            
            return {"message": "Documento atualizado com sucesso", "document_id": document_id_to_update, "new_version_hash": hash_document, "success": True}
        
        else:
            new_doc_id = metadata_service.create_document_record(
                filename, collection_name, hash_document, file_content, parent_document_id
            )
            return {"message": "Documento criado e indexado com sucesso", "document_id": new_doc_id, "hash": hash_document, "success": True}
    
    finally:
        os.remove(temp_filepath)


def delete_document_controller(doc_id: str, collection_name: str):
    metadata = metadata_service.get_document_by_id(doc_id)
    if not metadata:
        return {"message": "Documento não encontrado na base de metadados", "success": False}
    
    active_hash = metadata['active_version_hash']
    
    # Deleta os vetores do Qdrant
    qdrant_service.delete_by_doc_id(active_hash, collection_name)
    
    # Deleta o registro de metadados e o arquivo associado no GridFS (se não houver mais referências)
    metadata_service.delete_document_record(doc_id)
    
    return {"message": f"Documento ID '{doc_id}' deletado com sucesso", "success": True}


def download_document_controller(doc_hash: str):

    metadata = metadata_service.find_first_by_hash(doc_hash)
    if not metadata or "gridfs_file_id" not in metadata:
        return {"message": "Metadados do documento não encontrados.", "success": False}

    gridfs_file_id = metadata["gridfs_file_id"]
    gridfs_file = metadata_service.get_file_from_gridfs(gridfs_file_id)

    if not gridfs_file:
        return {"message": "Arquivo não encontrado no armazenamento GridFS.", "success": False}
    
    return {"message": "Arquivo encontrado e pronto para download.", "success": True, "file": gridfs_file}