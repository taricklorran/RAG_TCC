import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

class AnswerLLM:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.url = os.getenv("GEMINI_BASE_URL")
        self.url_completo = f"{self.url}{self.api_key}"
        
        if not self.api_key or not self.url:
            raise ValueError("GEMINI_API_KEY e GEMINI_BASE_URL devem ser definidos no arquivo .env")

        self.headers = {"Content-Type": "application/json"}

        with open("./src/prompts/prompt.md", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def answer_llm(self, question, base_url, reranked_result):
        
        all_chunks = []
        for doc_chunks in reranked_result.values():
            if not doc_chunks:
                continue
            filename = doc_chunks[0]["filename"]
            document_id = doc_chunks[0]["document_id"]
            blocos = [f"### Documento: {filename}\nId do Documento: {document_id}\n"]

            for chunk in doc_chunks:
                
                page = chunk.get("page", "N/A")
                blocos.append(f"#### Página do documento {page}\n{chunk['text']}")
            all_chunks.append("\n\n".join(blocos))

        context = "\n\n".join(all_chunks)

        prompt = self.prompt_template.replace("{context}", context).replace("{question}", question).replace("{base_url}", base_url)

        data = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }

        try:
            response = requests.post(self.url_completo, headers=self.headers, json=data, timeout=30)

            response.raise_for_status()
            result = response.json()

            if "candidates" in result and result["candidates"]:
                candidate = result["candidates"][0]
                if "content" in candidate and candidate["content"].get("parts"):
                    resposta_texto = candidate["content"]["parts"][0].get("text", "").strip()

                    if resposta_texto.startswith("```json"):
                        resposta_texto = resposta_texto.removeprefix("```json").removesuffix("```").strip()
                    elif resposta_texto.startswith("```"):
                        resposta_texto = resposta_texto.removeprefix("```").removesuffix("```").strip()

                    try:
                        resposta_json = json.loads(resposta_texto)
                        return resposta_json
                    except json.JSONDecodeError:
                        return {"resposta": resposta_texto} 

        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Erro na requisição: {str(e)}")
            return f"Erro ao conectar com a API: {str(e)}"
        except Exception as e:
            print(f"[ERRO] Erro inesperado: {str(e)}")
            return f"Ocorreu um erro inesperado: {str(e)}"
