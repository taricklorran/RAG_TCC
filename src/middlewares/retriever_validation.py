from fastapi import HTTPException


class RetrieverValidation:
    def query(question: str):
        if not question:
            raise HTTPException(status_code=400, detail="A pergunta não pode ser vazia.")
        return question