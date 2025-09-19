import os
import json
from collections import defaultdict
from dotenv import load_dotenv

from services.container import get_embedder_service, get_qdrant_service, get_metadata_service
from services.llm.answer_llm_service import AnswerLLM
from services.retrieving.reranker_service import Reranker
from services.retrieving.retriever_service import Retriever

load_dotenv()

MAXIMUM_CHUNK_TOP = int(os.getenv("MAXIMUM_CHUNK_TOP"))
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")
THRESHOLD = float(os.getenv("THRESHOLD"))
CONTEXT_WINDOW_SIZE = int(os.getenv("CONTEXT_WINDOW_SIZE", 5))

embedder_service = get_embedder_service()
qdrant_service = get_qdrant_service()
metadata_service = get_metadata_service()

def retriever(question: str, collections: list[str] | None = None, limit_context: bool = False):
    # 1. Busca inicial por similaridade
    vector_question = embedder_service.embed_text(question)

    relevant_collections = []
    if collections:
        print(f"INFO: Buscando nas coleções especificadas pelo usuário: {collections}")
        relevant_collections = collections
    else:
        print("INFO: Buscando nas coleções relevantes automaticamente.")
        # Busca as coleções relevantes para a pergunta
        relevant_collections = Retriever.search_relevant_collections(vector_question)
    
    if not relevant_collections:
        return {"message": "Nenhuma coleção relevante encontrada para a pergunta", "success": False}
    
    # 2. Busca inicial por similaridade em todas as coleções relevantes
    initial_chunks = qdrant_service.search_question(vector_question, MAXIMUM_CHUNK_TOP, relevant_collections, THRESHOLD)
    
    #-------------DEBUGGING----------------
    if initial_chunks:
        # 1. Coleta todos os scores de todos os chunks em uma única lista
        all_scores = [
            chunk['score'] 
            for chunk_list in initial_chunks.values() 
            for chunk in chunk_list
        ]
        
        # 2. Ordena a lista de scores do maior para o menor
        sorted_scores = sorted(all_scores, reverse=True)
        
        # 3. Pega os 3 primeiros scores (os maiores)
        top_3_scores = sorted_scores[:3]
        
        # 4. Imprime o resultado
        print(f"INFO: Os 3 maiores scores da busca inicial foram: {top_3_scores}")
    #-------------DEBUGGING----------------


    if not initial_chunks:
        return {"message": "Não foram encontrados documentos para a pergunta", "success": False}
    
    
    expanded_context_chunks = {}
    if limit_context:
        print(f"INFO: Usando estratégia de Janela de Contexto (+/- {CONTEXT_WINDOW_SIZE} páginas).")

        # Coleta as páginas e coleções dos chunks encontrados
        relevant_pages_by_doc = defaultdict(lambda: {'pages': set(), 'collection': ''})

        if len(relevant_collections) == 1:
            collection_name = relevant_collections[0]
            for doc_id, chunks in initial_chunks.items():
                relevant_pages_by_doc[doc_id]['collection'] = collection_name
                for chunk in chunks:
                    relevant_pages_by_doc[doc_id]['pages'].add(chunk['page'])
        
        else:
            for doc_id, chunks in initial_chunks.items():
                for chunk in chunks:
                    relevant_pages_by_doc[doc_id]['pages'].add(chunk['page'])

            # Encontra a coleção de cada documento (necessário para a busca no Qdrant)
            initial_doc_hashes = list(initial_chunks.keys())
            for collection_name in relevant_collections:
                records = metadata_service.get_documents_by_hashes(collection_name, initial_doc_hashes)
                for record in records:
                    relevant_pages_by_doc[record['active_version_hash']]['collection'] = collection_name

        # Busca os chunks dentro da janela de contexto para cada documento
        all_window_chunks = []
        for doc_hash, data in relevant_pages_by_doc.items():
            if not data['pages'] or not data['collection']:
                continue

            min_page = max(1, min(data['pages']) - CONTEXT_WINDOW_SIZE)
            max_page = max(data['pages']) + CONTEXT_WINDOW_SIZE
    
            chunks_from_window = qdrant_service.get_chunks_by_page_window(
                collection_name=data['collection'],
                doc_hash=doc_hash,
                min_page=min_page,
                max_page=max_page
            )
            all_window_chunks.extend(chunks_from_window)

        # Agrupa o resultado final no formato esperado pelo reranker
        temp_grouped = defaultdict(list)
        for chunk in all_window_chunks:
            temp_grouped[chunk['document_id']].append(chunk)
        expanded_context_chunks = dict(temp_grouped)
    
    else:
        print("INFO: Usando estratégia de Documento Inteiro.")
    
        # Encontrar todos os documentos relacionados
        initial_doc_hashes = list(initial_chunks.keys())
    
        # Busca os metadados dos documentos encontrados para obter seus IDs
        all_metadata_records = []
        for collection_name in relevant_collections:
            records = metadata_service.get_documents_by_hashes(collection_name, initial_doc_hashes)
            if records:
                print(f"  -> Encontrados {len(records)} registro(s) na coleção '{collection_name}'")
                all_metadata_records.extend(records)
    
        if not all_metadata_records:
            print("!!! ERRO CRÍTICO DE SINCRONIA: Hashes existem no Qdrant, mas não foram encontrados no MongoDB.")
            return {"message": "Falha de sincronia entre o banco de vetores e os metadados.", "success": False}
    
        print(f"[DEBUG 3] Total de {len(all_metadata_records)} registros de metadados encontrados.")
    
        doc_ids_found = [record['id'] for record in all_metadata_records]
        related_documents = metadata_service.find_related_documents(doc_ids_found)
        print(f"[DEBUG 4] Contexto expandido para {len(related_documents)} documentos relacionados.")

        # Agrupar os documentos relacionados por sua coleção original
        hashes_by_collection = defaultdict(list)
        for doc in related_documents:
            collection_name = doc.get("collection_name")
            doc_hash = doc.get("active_version_hash")
            if collection_name and doc_hash:
                hashes_by_collection[collection_name].append(doc_hash)

        # Buscar todos os chunks de todos os documentos, respeitando suas coleções
        for collection_name, hashes in hashes_by_collection.items():
            chunks_from_collection = qdrant_service.get_all_chunks_by_doc_hashes(collection_name, hashes)
            expanded_context_chunks.update(chunks_from_collection)

    total_chunks_recuperados = sum(len(chunks) for chunks in expanded_context_chunks.values())
    print(f"[DEBUG 5] Total de {total_chunks_recuperados} chunks recuperados de {len(expanded_context_chunks)} documento(s) para re-ranqueamento.")

    if not expanded_context_chunks:
        return {"message": "Não foi possível montar o contexto expandido para a resposta.", "success": False}

    # 6. Re-ranquear o contexto expandido
    
    inst_reranker = Reranker()
    reranked_result = inst_reranker.rerank(question, expanded_context_chunks)
    total_reranked = sum(len(chunks) for chunks in reranked_result.values())

    print(f"Contexto expandido para {len(expanded_context_chunks)} documento(s). Total de chunks re-ranqueados: {total_reranked}")

    if not any(reranked_result.values()):
        return {"message": "Após o re-ranqueamento, nenhum chunk foi considerado relevante o suficiente para a pergunta.", "success": False}

    # 7. Enviar para o LLM
    llm = AnswerLLM()

    answer = llm.answer_llm(question, BACKEND_BASE_URL, reranked_result)
    
    return answer

    #return reranked_result
    