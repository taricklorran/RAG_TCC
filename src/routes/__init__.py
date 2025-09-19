from fastapi import FastAPI

from routes import (collections_route, documents_route, generate_token_route,
                    retriever_route)


def include_routes(app: FastAPI):
    app.include_router(collections_route.router)
    app.include_router(documents_route.router)
    app.include_router(retriever_route.router)
    app.include_router(generate_token_route.router)

