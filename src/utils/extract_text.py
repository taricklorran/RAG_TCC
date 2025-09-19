# src/utils/extract_text.py
import os
import fitz  # PyMuPDF
import pytesseract
import re
import chardet
from PIL import Image
from collections import Counter


class ExtractTextService:
    @staticmethod
    def is_pdf_searchable(file_path: str, sample_pages: int = 5) -> bool:
        """
        Verifica se um PDF é pesquisável analisando uma amostra de páginas.
        Retorna True se encontrar uma quantidade razoável de texto nativo.
        """
        print("INFO: Verificando se o PDF é pesquisável...")
        try:
            doc = fitz.open(file_path)
            num_pages_to_check = min(len(doc), sample_pages)
            if num_pages_to_check == 0: return False
            total_text_len = sum(len(doc[i].get_text().strip()) for i in range(num_pages_to_check))
            doc.close()

            is_searchable = (total_text_len / num_pages_to_check) > 100 # Heurística
            print(f"INFO: PDF é considerado {'pesquisável' if is_searchable else 'não pesquisável (imagem)'}.")
            return is_searchable
        except Exception as e:
            print(f"ERRO ao verificar PDF: {e}")
            return False

    @staticmethod
    def extract_native_text_by_page(file_path: str) -> list[tuple[int, str]]:
        """Extrai texto de um PDF pesquisável usando PyMuPDF."""
        print("INFO: Extraindo texto nativo do PDF...")
        doc = fitz.open(file_path)
        pages = [(i + 1, page.get_text("text", sort=True) or "") for i, page in enumerate(doc)]
        doc.close()
        return pages

    @staticmethod
    def extract_ocr_text_by_page(file_path: str) -> list[tuple[int, str]]:
            """Aplica OCR em um PDF, usando PyMuPDF para renderizar as páginas como imagens."""
            print("INFO: Aplicando OCR no PDF...")
            doc = fitz.open(file_path)
            pages_text = []
            for i, page in enumerate(doc):
                print(f"  -> Processando OCR na página {i + 1} de {len(doc)}...")
                try:
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = pytesseract.image_to_string(img, lang='por')
                    pages_text.append((i + 1, ocr_text or ""))
                except Exception as e:
                    print(f"ERRO: Falha no OCR da página {i+1}: {e}")
                    pages_text.append((i + 1, ""))
            doc.close()
            print("INFO: Processo de OCR concluído.")
            return pages_text

    @staticmethod
    def extract_text(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".txt":
            with open(file_path, "rb") as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result["encoding"]
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(file_path, "r", encoding="latin-1") as f:
                    text = f.read()
            return text

        else:
            raise ValueError("Formato de arquivo não suportado")

    @staticmethod
    def identify_headers_footers(pages: list, lines_to_check: int = 4, frequency_threshold: float = 0.6) -> tuple[set, set]:
            header_candidates = []
            footer_candidates = []
            total_pages = len(pages)
            if total_pages < 3:
                return set(), set()
            for _, page_text in pages:
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                if not lines:
                    continue
                header_candidates.extend(lines[:lines_to_check])
                footer_candidates.extend(lines[-lines_to_check:])
            header_counts = Counter(header_candidates)
            footer_counts = Counter(footer_candidates)
            min_occurrences = int(total_pages * frequency_threshold)
            headers = {line for line, count in header_counts.items() if count >= min_occurrences}
            footers = {line for line, count in footer_counts.items() if count >= min_occurrences}
            return headers - footers, footers - headers

    @staticmethod
    def clean_page_text(page_text: str, headers: set, footers: set) -> str:
        lines = page_text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line in headers or stripped_line in footers:
                continue
            line = re.sub(r'^\s*\d+(?=[A-ZÀ-Ú])', '', stripped_line)
            if re.fullmatch(r'\s*\d+\s*', line):
                continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    @staticmethod
    def is_table_of_contents(page_text: str, threshold: int = 5) -> bool:
        toc_pattern = re.compile(r'\.{5,}\s*\d+')
        matches = toc_pattern.findall(page_text)
        return len(matches) >= threshold