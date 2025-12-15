from __future__ import annotations

import logging
import os
from io import BytesIO

import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def configure_tesseract(tesseract_cmd: str | None) -> None:
    if tesseract_cmd and tesseract_cmd.strip():
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def ocr_image_bytes(image_bytes: bytes, lang: str = "spa") -> str:
    try:
        img = Image.open(BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang=lang).strip()
    except Exception:
        logger.exception("Fallo OCR sobre imagen")
        return ""


def ocr_pdf_bytes(pdf_bytes: bytes, poppler_path: str | None, lang: str = "spa") -> str:
    """Convierte PDF a imagenes y hace OCR. Requiere Poppler instalado."""
    try:
        from pdf2image import convert_from_bytes

        kwargs = {}
        if poppler_path and poppler_path.strip():
            kwargs["poppler_path"] = poppler_path
        images = convert_from_bytes(pdf_bytes, **kwargs)

        parts: list[str] = []
        for img in images:
            parts.append(pytesseract.image_to_string(img, lang=lang))
        return "\n".join(parts).strip()
    except Exception:
        logger.exception("Fallo OCR sobre PDF (pdf2image/poppler)")
        return ""
