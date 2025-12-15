from __future__ import annotations

import logging
from io import BytesIO

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrae texto si el PDF es nativo. Si no hay texto, devuelve string vacio."""
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            parts: list[str] = []
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    parts.append(txt)
            return "\n".join(parts).strip()
    except Exception:
        logger.exception("Fallo extrayendo texto nativo del PDF")
        return ""
