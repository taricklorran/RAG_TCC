# documents_route.py
import io
from fastapi import APIRouter, Depends, File, Query, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from controllers.document_controller import (delete_document_controller,
                                             upload_document_controller, download_document_controller)
from middlewares.collection_validation import CollectionValidation
from middlewares.document_validation import DcoumentValidation
from middlewares.token_validation import bearer_token_validation
from services.container import get_metadata_service
from utils.hashing import hash_file

router = APIRouter(
    prefix="/document",
    tags=["Documentos"]
)

@router.post("/upload", dependencies=[Depends(bearer_token_validation)])
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = Query(...),
    document_id_to_update: str = Query(None, description="ID do documento a ser ATUALIZADO (versionamento)."),
    parent_document_id: str = Query(None, description="ID do documento principal ao qual este novo se relaciona (ex: Contrato Pai).")
):
    contents = await file.read()
    hash_document = hash_file(contents)

    CollectionValidation.collection_name_not_empty(collection_name)
    CollectionValidation.collection_exists(collection_name)
    DcoumentValidation.document_extension(file.filename)
    DcoumentValidation.document_exists(hash_document, collection_name)

    if document_id_to_update:
        DcoumentValidation.document_id_exists(document_id_to_update)
    else:
        pass
    
    if parent_document_id:
        DcoumentValidation.document_id_exists(parent_document_id)

    # Chama o controller, passando o conteúdo do arquivo
    response = upload_document_controller(
        hash_document=hash_document,
        file_content=contents,
        filename=file.filename,
        collection_name=collection_name,
        document_id_to_update=document_id_to_update,
        parent_document_id=parent_document_id
    )
        
    return response

@router.delete("/{doc_id}", dependencies=[Depends(bearer_token_validation)])
def delete_document(doc_id: str, collection_name: str = Query(...)):
    CollectionValidation.collection_name_not_empty(collection_name)
    CollectionValidation.collection_exists(collection_name)
    DcoumentValidation.document_id_not_empty(doc_id)
    DcoumentValidation.document_id_exists(doc_id)
    return delete_document_controller(doc_id, collection_name)

@router.get("/download/{doc_hash}")
def download_document(doc_hash: str):

    document_file = download_document_controller(doc_hash)
    if not document_file["success"]:
        raise HTTPException(status_code=404, detail=document_file["message"])
    
    gridfs_file = document_file.get("file")

# Verificação de segurança caso a chave 'file' não exista por algum motivo
    if not gridfs_file:
        raise HTTPException(status_code=500, detail="Arquivo não encontrado no resultado do controller.")
    
    return StreamingResponse(
        content=io.BytesIO(gridfs_file.read()),

        media_type=gridfs_file.content_type,

        headers={"Content-Disposition": f"attachment; filename=\"{gridfs_file.filename}\""}
    )
    
