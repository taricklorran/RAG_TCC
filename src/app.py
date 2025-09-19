"""Módulo principal da aplicação FastAPI. Define o app, aplica middlewares e carrega as rotas."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# função que inclui todas as rotas
from routes import include_routes

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carregar rotas
include_routes(app)

# Expor para server.py
def get_app():
    return app