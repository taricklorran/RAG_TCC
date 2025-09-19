# src/services/database/metadata_service.py
import os
from datetime import datetime
import pymongo
from bson.objectid import ObjectId, InvalidId
import gridfs

class MetadataService:
    def __init__(self):
        """Inicializa a conexão com o MongoDB."""
        mongo_uri = os.getenv("MONGO_URI")
        db_name = os.getenv("MONGO_DB_NAME")
        if not mongo_uri or not db_name:
            raise ValueError("MONGO_URI e MONGO_DB_NAME devem ser definidos no arquivo .env")
        
        self.client = pymongo.MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db["documents"]
        self.fs = gridfs.GridFS(self.db)

    def _serialize_document(self, doc):
        """Converte o _id do MongoDB para uma string 'id'."""
        if doc:
            doc['id'] = str(doc['_id'])
            del doc['_id']
        return doc
    
    def save_file(self, file_content: bytes, filename: str, doc_hash: str) -> ObjectId:
        """Salva o conteúdo do arquivo no GridFS e retorna o ID do arquivo."""
        file_id = self.fs.put(
            file_content,
            filename=filename,
            doc_hash=doc_hash,
            contentType=f"application/{filename.split('.')[-1]}"
        )
        return file_id

    def create_document_record(self, filename: str, collection_name: str, doc_hash: str, file_content: bytes, parent_id: str | None = None) -> str:
        """Cria um novo registro de metadados para um documento."""

        # Salva o arquivo no GridFS e obtém seu ID
        gridfs_file_id = self.save_file(file_content, filename, doc_hash)

        # Cria nosso registro de metadados com a referência ao arquivo no GridFS
        now = datetime.now()
        document_data = {
            "original_filename": filename,
            "collection_name": collection_name,
            "active_version_hash": doc_hash,
            "gridfs_file_id": gridfs_file_id,
            "created_at": now,
            "updated_at": now,
            "parent_id": parent_id if parent_id else None
        }
        result = self.collection.insert_one(document_data)
        return str(result.inserted_id)

    def get_document_by_id(self, doc_id: str) -> dict | None:
        """Busca um documento pelos seus metadados usando o ID (ObjectId)."""
        if isinstance(doc_id, str) and '=' in doc_id:
            cleaned_id = doc_id.split('=')[-1].strip()
            print(f"INFO: ID de documento corrigido de '{doc_id}' para '{cleaned_id}'")
            doc_id = cleaned_id
            
        try:
            record = self.collection.find_one({"_id": ObjectId(doc_id)})
            return self._serialize_document(record)
        except InvalidId:
            return None

    def get_document_by_hash(self, collection_name: str, doc_hash: str) -> dict | None:
        """Verifica se um hash de documento já existe em uma coleção."""
        record = self.collection.find_one(
            {"collection_name": collection_name, "active_version_hash": doc_hash}
        )
        return self._serialize_document(record)

    def update_document_version(self, doc_id: str, new_hash: str, new_filename: str, new_gridfs_file_id: ObjectId):
        """Atualiza o hash da versão ativa e o ID do arquivo no GridFS."""
        self.collection.update_one(
            {"_id": ObjectId(doc_id)},
            {
                "$set": {
                    "active_version_hash": new_hash,
                    "original_filename": new_filename,
                    "gridfs_file_id": new_gridfs_file_id,
                    "updated_at": datetime.now()
                }
            }
        )
    
    def find_first_by_hash(self, doc_hash: str) -> dict | None:
        """Busca o primeiro registro de metadados que corresponde a um hash."""
        if isinstance(doc_hash, str) and '=' in doc_hash:
            cleaned_hash = doc_hash.split('=')[-1].strip()
            print(f"INFO: ID de documento corrigido de '{doc_hash}' para '{cleaned_hash}'")
            doc_hash = cleaned_hash
        record = self.collection.find_one({"active_version_hash": doc_hash})
        return self._serialize_document(record)
    
    def get_file_from_gridfs(self, file_id: ObjectId):
        """Busca um arquivo do GridFS pelo seu ID."""
        try:
            return self.fs.get(file_id)
        except gridfs.errors.NoFile:
            return None
        
    def delete_file_from_gridfs(self, file_id: ObjectId):
        """Deleta um arquivo do GridFS."""
        if self.fs.exists(file_id):
            self.fs.delete(file_id)

    def delete_document_record(self, doc_id: str):
        """Deleta o registro de metadados de um documento."""
        metadata = self.get_document_by_id(doc_id)
        if metadata and 'gridfs_file_id' in metadata:
            self.delete_file_from_gridfs(metadata['gridfs_file_id'])
        self.collection.delete_one({"_id": ObjectId(doc_id)})

    def get_documents_by_hashes(self, collection_name: str, doc_hashes: list[str]) -> list[dict]:
        """Busca os metadados de múltiplos documentos a partir de seus hashes."""
        records = self.collection.find({
            "collection_name": collection_name,
            "active_version_hash": {"$in": doc_hashes}
        })
        return [self._serialize_document(doc) for doc in records]

    def find_related_documents(self, doc_ids: list[str]) -> list[dict]:
        """
        Encontra todos os documentos relacionados (pais e filhos) a uma lista de IDs.
        """
        # Converte os IDs de string para ObjectId para a consulta
        object_ids = [ObjectId(doc_id) for doc_id in doc_ids if ObjectId.is_valid(doc_id)]
        
        # Encontra os documentos originais para obter seus parent_ids (se tiverem)
        initial_docs = list(self.collection.find({"_id": {"$in": object_ids}}))
        
        # Coleta todos os IDs de documentos e de pais envolvidos
        all_related_ids = set(doc['_id'] for doc in initial_docs)
        for doc in initial_docs:
            if doc.get('parent_id'):
                try:
                    all_related_ids.add(ObjectId(doc['parent_id']))
                except InvalidId:
                    continue # Ignora parent_id inválido

        final_docs_cursor = self.collection.find({
            "$or": [
                {"_id": {"$in": list(all_related_ids)}},
                {"parent_id": {"$in": [str(oid) for oid in all_related_ids]}}
            ]
        })
        
        return [self._serialize_document(doc) for doc in final_docs_cursor]