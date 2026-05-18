"""
Extração e validação de texto de documentos contratuais.

Suporta documentos com o mesmo conteúdo operacional em formatos diferentes
(PDF, XLSX/XLS, DOCX, TXT/MD/RTF).
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Optional
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd


SUPPORTED_CONTRACT_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".docx",
    ".txt",
    ".md",
    ".rtf",
}

_INVALID_ANALYSIS_MARKERS = (
    "nenhum arquivo de contrato carregado",
    "ferramenta de leitura retornou que nenhum arquivo de contrato foi carregado",
    "nao ha clausulas contratuais especificas",
    "não há cláusulas contratuais específicas",
    "defaults operacionais",
    "[nenhum arquivo de contrato carregado]",
)


@dataclass
class ContractTextExtraction:
    ok: bool
    path: str
    ext: str
    parser: str
    text: str
    total_chars: int
    pages_total: int = 0
    pages_with_text: int = 0
    sheets_total: int = 0
    keywords_found: int = 0
    warning: Optional[str] = None
    error: Optional[str] = None

    def summary(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "ext": self.ext,
            "parser": self.parser,
            "total_chars": self.total_chars,
            "pages_total": self.pages_total,
            "pages_with_text": self.pages_with_text,
            "sheets_total": self.sheets_total,
            "keywords_found": self.keywords_found,
            "warning": self.warning,
            "error": self.error,
        }


def _extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as zf:
        xml = zf.read("word/document.xml")

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    for p in root.findall(".//w:p", ns):
        runs: list[str] = []
        for t in p.findall(".//w:t", ns):
            if t.text:
                runs.append(t.text)
        if runs:
            paragraphs.append("".join(runs).strip())
    return "\n".join([p for p in paragraphs if p])


def _extract_pdf_text(path: Path) -> tuple[str, int, int]:
    import pdfplumber

    pages: list[str] = []
    pages_with_text = 0
    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        for idx, page in enumerate(pdf.pages):
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                try:
                    words = page.extract_words() or []
                except Exception:
                    words = []
                if words:
                    page_text = " ".join(str(w.get("text", "")).strip() for w in words if w.get("text")).strip()
            if page_text:
                pages_with_text += 1
                pages.append(f"[Pagina {idx + 1}/{total_pages}]\n{page_text}")
    return "\n\n".join(pages), total_pages, pages_with_text


def _count_keywords(text: str) -> int:
    kws = (
        "cardapio",
        "refeicao",
        "gramatura",
        "incidencia",
        "proibicao",
        "restricao",
        "dieta",
        "licitacao",
        "proposta",
        "fornecimento",
        "almoco",
        "jantar",
    )
    normalized = (
        text.lower()
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ã", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return sum(1 for kw in kws if kw in normalized)


def extract_contract_text(path_like: Optional[str | Path]) -> ContractTextExtraction:
    path = Path(str(path_like or "")).expanduser()
    if not str(path_like or "").strip():
        return ContractTextExtraction(
            ok=False,
            path=str(path),
            ext="",
            parser="none",
            text="",
            total_chars=0,
            error="Caminho do documento nao informado.",
        )
    if not path.exists():
        return ContractTextExtraction(
            ok=False,
            path=str(path),
            ext=path.suffix.lower(),
            parser="none",
            text="",
            total_chars=0,
            error="Arquivo nao encontrado no servidor. Reenvie o documento.",
        )

    ext = path.suffix.lower()
    if ext not in SUPPORTED_CONTRACT_EXTENSIONS:
        return ContractTextExtraction(
            ok=False,
            path=str(path),
            ext=ext,
            parser="none",
            text="",
            total_chars=0,
            error=f"Formato '{ext}' nao suportado.",
        )

    try:
        parser = "unknown"
        pages_total = 0
        pages_with_text = 0
        sheets_total = 0
        text = ""

        if ext == ".pdf":
            parser = "pdfplumber"
            text, pages_total, pages_with_text = _extract_pdf_text(path)
        elif ext in {".xlsx", ".xls"}:
            parser = "pandas-excel"
            sheets = pd.read_excel(path, sheet_name=None, dtype=str)
            sheets_total = len(sheets)
            parts: list[str] = []
            for sheet_name, df in sheets.items():
                parts.append(f"--- Aba: {sheet_name} ---")
                safe_df = df.fillna("")
                parts.append(safe_df.to_string(index=False))
            text = "\n".join(parts)
        elif ext == ".docx":
            parser = "docx-xml"
            text = _extract_docx_text(path)
        else:
            parser = "plain-text"
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1", errors="ignore")
            # RTF normalmente vem com tags; deixa uma limpeza minima
            if ext == ".rtf":
                text = re.sub(r"\\[a-z]+-?\d* ?", " ", text)
                text = re.sub(r"[{}]", " ", text)

        text = re.sub(r"[ \t]+", " ", text or "")
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        total_chars = len(text)
        kw_hits = _count_keywords(text)
        warning = None
        if total_chars < 300:
            warning = "Texto extraido muito curto para analise confiavel."
        elif kw_hits == 0:
            warning = "Documento sem palavras-chave de contrato/cardapio detectadas."

        return ContractTextExtraction(
            ok=total_chars > 0,
            path=str(path),
            ext=ext,
            parser=parser,
            text=text,
            total_chars=total_chars,
            pages_total=pages_total,
            pages_with_text=pages_with_text,
            sheets_total=sheets_total,
            keywords_found=kw_hits,
            warning=warning,
        )
    except Exception as exc:
        return ContractTextExtraction(
            ok=False,
            path=str(path),
            ext=ext,
            parser="error",
            text="",
            total_chars=0,
            error=str(exc),
        )


def analysis_looks_invalid(regras: Optional[dict[str, Any]]) -> bool:
    if not isinstance(regras, dict) or not regras:
        return True
    payload = json.dumps(regras, ensure_ascii=False).lower()
    return any(marker in payload for marker in _INVALID_ANALYSIS_MARKERS)


def build_contract_extraction_error(extraction: ContractTextExtraction) -> str:
    details = extraction.error or extraction.warning or "Nao foi possivel extrair texto util do arquivo."
    return (
        "Nao foi possivel analisar o documento enviado. "
        f"{details} "
        "Reenvie em formato com texto selecionavel (PDF pesquisavel, XLSX, DOCX ou TXT)."
    )
