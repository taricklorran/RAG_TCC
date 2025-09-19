from sentence_transformers import SentenceTransformer


class EmbedderService:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def get_embedding_dimension(self) -> int:
        """Retorna a dimensão do vetor do modelo."""
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str):
        """Gera o embedding para um único texto."""
        return self.model.encode(text).tolist()

    def embed_chunks(self, chunks: list[dict]) -> list[list[float]]:
        """Gera os embeddings para uma lista de chunks."""
        texts = [chunk["text"] for chunk in chunks]
        return self.model.encode(texts).tolist()
