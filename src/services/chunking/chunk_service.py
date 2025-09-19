# src/services/chunking/chunk_service.py
import os
import nltk
from dotenv import load_dotenv
from langdetect import LangDetectException, detect
from nltk.tokenize import sent_tokenize
from utils.extract_text import ExtractTextService

load_dotenv()

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP"))

# Configurar o caminho para os dados do NLTK
nltk.data.path.append('./nltk_data')
try:
    nltk.data.find("tokenizers/punkt/english.pickle")
    nltk.data.find("tokenizers/punkt/portuguese.pickle")
except LookupError:
    print("INFO: Baixando pacotes necessários do NLTK (punkt, wordnet, omw-1.4)...")
    nltk.download('punkt')
    nltk.download('wordnet')
    nltk.download('omw-1.4')
    print("INFO: Download do NLTK concluído.")


class ChunkerService:
    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = overlap
    
    def detect_language(self, text: str) -> str:
        try:
            lang = detect(text)
            return 'portuguese' if lang == 'pt' else 'english'
        except LangDetectException:
            return 'english'

    def chunk_document(self, file_path: str, doc_id: str, filename: str):
        
        if os.path.splitext(file_path)[1].lower() == ".pdf":
            if ExtractTextService.is_pdf_searchable(file_path):
                pages = ExtractTextService.extract_native_text_by_page(file_path)
            else:
                pages = ExtractTextService.extract_ocr_text_by_page(file_path)
        else:
            pages = [(1, ExtractTextService.extract_text(file_path))]

        if not pages:
            print(f"INFO: Nenhum texto extraído do documento '{filename}'.")
            return {"message": f"Nenhum texto extraído do documento '{filename}'.", "success": False, }

        headers, footers = ExtractTextService.identify_headers_footers(pages)
        
        if headers or footers:
            print(f"INFO: Identificados {len(headers)} cabeçalhos e {len(footers)} rodapés para o documento '{filename}'.")

        chunks = []
        chunk_id = 0

        current_chunk_tokens = []
        current_length = 0
        
        for page_number, page_text_raw in pages:
            if ExtractTextService.is_table_of_contents(page_text_raw):
                print(f"INFO: Página {page_number} ignorada por ser um sumário.")
                continue

            page_text = ExtractTextService.clean_page_text(page_text_raw, headers, footers)
            if not page_text.strip():
                continue  # ignora páginas vazias

            language = self.detect_language(page_text)
            sentences = sent_tokenize(page_text, language=language)

            print(f"\n\nTokenização utilizando NLTK para o idioma: {language}")
            print(f"{sentences}")
            print(f"\n\n")

            print(f"TOKENS:\n")
            i = 1
            for sentence in sentences:
                if not sentence.strip():
                    continue
                tokens = sentence.split()
                if not tokens:
                    continue
                    
                print(f"{i} - {tokens}")
                i += 1

                if current_length + len(tokens) > self.chunk_size and current_chunk_tokens:
                    chunks.append({
                        "text": " ".join(current_chunk_tokens),
                        "doc_id": doc_id,
                        "filename": filename,
                        "chunk_id": chunk_id,
                        "page": page_number
                    })
                    chunk_id += 1

                    overlap_index = max(0, len(current_chunk_tokens) - self.chunk_overlap)
                    current_chunk_tokens = current_chunk_tokens[overlap_index:]
                    current_length = len(current_chunk_tokens)

                current_chunk_tokens.extend(tokens)
                current_length += len(tokens)

        if current_chunk_tokens:
            chunks.append({
                "text": " ".join(current_chunk_tokens),
                "doc_id": doc_id,
                "filename": filename,
                "chunk_id": chunk_id,
                "page": page_number
            })
            chunk_id += 1

        print(f"\n\nCHUNKS:\n{chunks}\n\n")

        return chunks
