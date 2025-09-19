from fastapi import APIRouter, Depends, Query

from controllers.retriever_controller import retriever
from middlewares.retriever_validation import RetrieverValidation
from middlewares.token_validation import bearer_token_validation

# Aplica o middleware de token em todas as rotas deste router
router = APIRouter(
    prefix="/ask",
    tags=["Perguntas"],
    dependencies=[Depends(bearer_token_validation)]
)

@router.get("/")
async def ask(query: str,
              collections: list[str] | None = Query(None, description="(Opcional) Lista de coleções para a busca. Se omitido, o sistema tentará detectar as mais relevantes."),
              limit_context: bool = Query(False, description="Se True, busca um contexto limitado (+/- N páginas). Se False, busca o documento inteiro.")):
    RetrieverValidation.query(query)
    retrieved_chunks = retriever(query, collections, limit_context)
    return retrieved_chunks