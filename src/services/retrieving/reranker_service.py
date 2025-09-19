# reranker_service.py
import os
import torch
from collections import defaultdict

from dotenv import load_dotenv
from sentence_transformers import CrossEncoder

load_dotenv()

RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME")
MAXIMUM_CHUNK_TOP = int(os.getenv("RERANKER_MAXIMUM_CHUNK_TOP"))
THRESHOLD_RERANKER = float(os.getenv("THRESHOLD_RERANKER"))

class Reranker:
    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        print(f"INFO: Carregando o modelo de re-ranqueamento '{RERANKER_MODEL_NAME}' no dispositivo: {self.device}")

        self.model = CrossEncoder(RERANKER_MODEL_NAME)
        self.threshold = THRESHOLD_RERANKER
        self.max_chunks = MAXIMUM_CHUNK_TOP

    def rerank(self, question: str, chunks_by_doc: dict) -> dict:
        """
        Executa o re-ranqueamento global em todos os chunks recuperados.
        """
        # Juntar todos os chunks de todos os documentos em uma única lista
        all_chunks = []
        for doc_id, chunks in chunks_by_doc.items():
            all_chunks.extend(chunks)

        if not all_chunks:
            return {}

        # Criar os pares [pergunta, texto] para o modelo
        pairs = [[question, chunk["text"]] for chunk in all_chunks]
        
        # Executar a predição uma vez para todos os pares
        print("INFO: Iniciando o processo de re-ranqueamento...")
        scores = self.model.predict(pairs, show_progress_bar=True)
        print("INFO: Re-ranqueamento concluído.")

        # Atribuir os scores e ordenar a lista global de chunks
        for chunk, score in zip(all_chunks, scores):
            chunk["rerank_score"] = float(score)

        sorted_chunks = sorted(all_chunks, key=lambda x: x["rerank_score"], reverse=True)

        # Filtrar a lista global pelo limiar de relevância
        relevant_chunks = [chunk for chunk in sorted_chunks if chunk["rerank_score"] >= self.threshold]

        final_chunks = relevant_chunks[:self.max_chunks]
        
        # Reagrupar os chunks finais por seu 'document_id' original
        # Isso mantém o formato de saída esperado pelo serviço do LLM
        reranked_result = defaultdict(list)
        for chunk in final_chunks:
            doc_id = chunk["document_id"]
            reranked_result[doc_id].append(chunk)

        return dict(reranked_result)