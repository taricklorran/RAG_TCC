import os

import numpy as np
from dotenv import load_dotenv

from services.container import get_embedder_service
from services.description_collections import DESCRICOES

load_dotenv()

MAXIMUM_CHUNK_TOP = int(os.getenv("MAXIMUM_CHUNK_TOP"))
THRESHOLD = float(os.getenv("THRESHOLD"))

embedder_service = get_embedder_service()

class Retriever:
    @staticmethod
    def search_relevant_collections(vector_question):
        # chama o método estático rate_question para avaliar as coleções
        relevant_collections = Retriever.rate_question(vector_question)
        return relevant_collections
    
    @staticmethod
    def rate_question(vector_question):
        """Avalia quais coleções são mais relevantes para a pergunta."""
        scores = {}

        # para cada coleção, calcula a média dos embeddings das descrições
        for nome, descricoes in DESCRICOES.items():
            # cria lista de embeddings para cada descrição
            desc_embs = [embedder_service.embed_text(desc) for desc in descricoes]
            desc_emb = np.mean(np.array(desc_embs), axis=0)
            score = Retriever.cosine_similarity(vector_question, desc_emb)
            scores[nome] = score

        for nome, score in scores.items():
            print(f"Similaridade com '{nome}': {score:.4f}")

        # Retorna coleções com score acima do threshold
        colecoes_relevantes = [nome for nome, score in scores.items() if score >= THRESHOLD]

        # fallback: retorna a melhor se nenhuma passou do threshold
        if not colecoes_relevantes:
            melhor = max(scores.items(), key=lambda x: x[1])
            return [melhor[0]]

        return colecoes_relevantes

    @staticmethod
    def cosine_similarity(a, b):
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
