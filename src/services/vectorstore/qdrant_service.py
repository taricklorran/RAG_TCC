# src/services/vectorstore/qdrant_service.py
import uuid
from collections import defaultdict
from typing import Any, Dict, List

from qdrant_client.http.models import Range
from qdrant_client import QdrantClient
from qdrant_client.http.models import (Distance, FieldCondition, Filter,
                                       MatchValue, PointStruct, VectorParams)


class QdrantService:
    def __init__(self, client: QdrantClient, model=None):
        self.client = client
        self.model = model

    def collection_exists(self, collection_name: str) -> bool:
        try:
            return self.client.get_collection(collection_name) is not None
        except Exception:
            return False

    def create_collection(self, collection_name: str, vector_size: int) -> bool:
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao criar coleção: {e}")
            return False
        

    def delete_collection(self, collection_name: str) -> bool:
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao deletar coleção: {e}")
            return False

    def index_chunks(self, chunks: List[Dict[str, Any]], collection_name: str, vectors: List[List[float]]) -> None:

        try:
            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "text": chunk["text"],
                        "doc_id": chunk["doc_id"],
                        "filename": chunk["filename"],
                        "chunk_id": chunk["chunk_id"],
                        "page": chunk.get("page")
                    }
                )
                for chunk, vector in zip(chunks, vectors)
            ]
            response = self.client.upsert(collection_name=collection_name, points=points)

            return response.status == "completed"
        except Exception as e:
            print(f"[ERRO] Falha ao indexar chunks: {e}")
            return False
        

    def delete_by_doc_id(self, doc_id: str, collection_name: str) -> bool:
        try:
            result = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
                limit=1
            )
            if not result[0]:
                return False

            self.client.delete(
                collection_name=collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                )
            )
            return True
        except Exception as e:
            print(f"[ERRO] Falha ao excluir doc_id={doc_id}: {e}")
            return False

    def document_exists(self, doc_id: str, collection_name: str) -> bool:
        """doc_id é o hash do documento."""
        try:
            result_points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [{
                        "key": "doc_id",
                        "match": {"value": doc_id}
                    }]
                },
                limit=1
            )
            return len(result_points) > 0
        except Exception as e:
            print(f"Erro ao verificar documento no Qdrant: {e}")
            return False

    def list_collections(self) -> List[str]:
        return self.client.get_collections()
    
    def get_collection(self, collection_name: str) -> Dict[str, Any]:
        try:
            collection_info = self.client.get_collection(collection_name)
            return {
                "collection": {
                    "name": collection_name,
                    "status": collection_info.status,
                    "vectors_count": collection_info.vectors_count,
                    "points_count": collection_info.points_count,
                    "segments_count": collection_info.segments_count
                }
            }
        except Exception as e:
            print(f"Erro ao obter informações da coleção: {e}")
            return {
                "collection": None,
                "error": str(e),
            }
    
    def search_question(self, vector_question: str, maximum_chunk_top: int, relevant_collections: List[str], score_threshold) -> Dict[str, List[Dict[str, Any]]]:
        """
        Busca os documentos mais relevantes para a pergunta, aplicando um limiar de score.
        """

        grouped = defaultdict(list)
        for collection_name in relevant_collections:
            try:
                results = self.client.search(
                    collection_name=collection_name,
                    query_vector=vector_question,
                    limit=maximum_chunk_top,
                    with_payload=True,
                    score_threshold=score_threshold
                )

                for hit in results:
                    if hit.score < score_threshold:
                        continue #Pular resultados abaixo do limiar

                    payload = hit.payload
                    doc_id = payload.get("doc_id", "desconhecido")
                    
                    grouped[doc_id].append({
                        "text": payload["text"],
                        "document_id": doc_id,
                        "filename": payload.get("filename", "desconhecido"),
                        "chunk_index": payload.get("chunk_id", -1),
                        "page": payload.get("page", None),
                        "score": hit.score,
                    })
            except Exception as e:
                print(f"[ERRO] Falha ao buscar em {collection_name}: {e}")

        # Ordenar por score decrescente
        for doc_id in grouped:
            grouped[doc_id] = sorted(grouped[doc_id], key=lambda x: x["score"], reverse=True)

        return dict(grouped)
    
    def get_chunks_by_page_window(self, collection_name: str, doc_hash: str, min_page: int, max_page: int) -> list:
        """
        Busca todos os chunks de um documento que estão dentro de uma janela de páginas.
        """
        try:
            retrieved_points, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="doc_id", match={"value": doc_hash}),
                        FieldCondition(key="page", range=Range(gte=min_page, lte=max_page))
                    ]
                ),
                limit=1000, # Limite alto para garantir que todos os chunks da janela sejam pegos
                with_payload=True
            )
            
            # Formata a saída para ser uma lista simples de chunks
            chunks = []
            for point in retrieved_points:
                payload = point.payload
                chunks.append({
                    "text": payload["text"],
                    "document_id": payload.get("doc_id"),
                    "filename": payload.get("filename"),
                    "chunk_index": payload.get("chunk_id"),
                    "page": payload.get("page"),
                    "score": 1.0 
                })
            return chunks

        except Exception as e:
            print(f"[ERRO] Falha ao buscar janela de páginas em {collection_name}: {e}")
            return []
    
    def get_all_chunks_by_doc_hashes(self, collection_name: str, doc_hashes: list[str]) -> dict:
        """
        Busca todos os chunks de uma lista de hashes de documentos.
        Retorna um dicionário agrupado pelo hash (doc_id).
        """
        if not doc_hashes:
            return {}

        retrieved_points, next_offset = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="doc_id", match={"any": doc_hashes})
                ]
            ),
            limit=1000,
            with_payload=True
        )
        
        # Agrupa os resultados por doc_id (hash)
        grouped_chunks = defaultdict(list)
        for point in retrieved_points:
            payload = point.payload
            doc_id = payload.get("doc_id")
            grouped_chunks[doc_id].append({
                "text": payload["text"],
                "document_id": doc_id,
                "filename": payload.get("filename", "desconhecido"),
                "chunk_index": payload.get("chunk_id", -1),
                "page": payload.get("page", None),
                "score": 1.0
            })
            
        return dict(grouped_chunks)

        
