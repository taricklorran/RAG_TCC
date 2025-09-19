from fastapi import APIRouter, Depends

from controllers.collection_controller import (create_collection_controller,
                                               delete_collection_controller,
                                               get_collection_controller,
                                               list_collections_controller)
from middlewares.collection_validation import CollectionValidation
from middlewares.token_validation import bearer_token_validation

router = APIRouter(
    prefix="/collection",
    tags=["Colelções"],
    dependencies=[Depends(bearer_token_validation)]
)

@router.post("/create")
def create_collection(collection_name: str):
    CollectionValidation.collection_name_not_empty(collection_name)
    CollectionValidation.collection_does_not_exist(collection_name)
    return create_collection_controller(collection_name, vector_size=384)

@router.get("/list")
def list_collections():
    return list_collections_controller()

@router.get("/")
def get_collection(collection_name: str):
    CollectionValidation.collection_name_not_empty(collection_name)
    CollectionValidation.collection_exists(collection_name)
    return get_collection_controller(collection_name)

@router.delete("/")
def delete_collection(collection_name: str):
    CollectionValidation.collection_name_not_empty(collection_name)
    CollectionValidation.collection_exists(collection_name)
    return delete_collection_controller(collection_name)