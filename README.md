# RAG Project

Este é um projeto de RAG (Retrieval-Augmented Generation) que utiliza um modelo de linguagem para responder a perguntas com base em um conjunto de documentos.

## Pré-requisitos

- Python 3.10+
- Docker
- Git

## Começando

### 1. Clone o Repositório

```bash
git clone https://github.com/taricklorran/RAG_TCC.git
cd rag_project
```

### 2. Crie e Ative um Ambiente Virtual

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows use `.venv\Scripts\activate`
```

### 3. Instale as Dependências

Instale as bibliotecas Python necessárias a partir do arquivo `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4. Suba o Container do Qdrant

Este projeto utiliza o Qdrant como vector store. Para rodar o Qdrant em um container Docker, execute o seguinte comando:

```bash
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```
Isso irá baixar a imagem do Qdrant e iniciar um container. Suas coleções serão persistidas no diretório `qdrant_storage` na raiz do projeto.

## Rodando a Aplicação

Para iniciar o servidor, execute o seguinte comando:

```bash
python src/server.py
```

O servidor estará rodando em `http://localhost:8000`.

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto e adicione as seguintes variáveis de ambiente:

```
QDRANT_URL="http://localhost:6333"
JWT_SECRET_KEY="your-secret-key"
MAXIMUM_CHUNK_TOP=10
BACKEND_BASE_URL="http://localhost:8000"
THRESHOLD=0.5
CONTEXT_WINDOW_SIZE=5
PORT=8000
CHUNK_SIZE=1024
CHUNK_OVERLAP=200
MODEL_NAME="text-embedding-004"
MONGO_URI="your-mongo-uri"
MONGO_DB_NAME="your-mongo-db-name"
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"
RERANKER_MODEL_NAME="rerank-english-v2.0"
RERANKER_MAXIMUM_CHUNK_TOP=5
THRESHOLD_RERANKER=0.8
```

## Estrutura do Projeto

```
.
├── .gitattributes
├── .gitignore
├── README.md
├── requirements.txt
├── src
│   ├── app.py
│   ├── server.py
│   ├── config
│   │   └── qdrant.py
│   ├── controllers
│   │   ├── collection_controller.py
│   │   ├── document_controller.py
│   │   ├── generate_token_controller.py
│   │   └── retriever_controller.py
│   ├── middlewares
│   │   ├── collection_validation.py
│   │   ├── document_validation.py
│   │   ├── retriever_validation.py
│   │   └── token_validation.py
│   ├── prompts
│   │   └── prompt.md
│   ├── routes
│   │   ├── collections_route.py
│   │   ├── documents_route.py
│   │   ├── generate_token_route.py
│   │   └── retriever_route.py
│   ├── services
│   │   ├── container.py
│   │   ├── description_collections.py
│   │   ├── chunking
│   │   ├── database
│   │   ├── embedding
│   │   ├── llm
│   │   ├── retrieving
│   │   └── vectorstore
│   └── utils
│       ├── extract_text.py
│       └── hashing.py
└── temp
```
