import os
import shutil
from io import BytesIO

import pytest

from src.services.ocr_service import configure_tesseract, ocr_pdf_bytes
from src.services.pdf_service import extract_text_from_pdf


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION", "").strip() == "1"


def _configure_from_env() -> tuple[str | None, str | None]:
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    poppler_path = os.getenv("POPPLER_PATH")
    configure_tesseract(tesseract_cmd)
    return tesseract_cmd, poppler_path


def _has_poppler(poppler_path: str | None) -> bool:
    if poppler_path and poppler_path.strip():
        exe = os.path.join(poppler_path, "pdfinfo.exe")
        return os.path.exists(exe)
    return shutil.which("pdfinfo") is not None


def _has_tesseract(tesseract_cmd: str | None) -> bool:
    if tesseract_cmd and tesseract_cmd.strip():
        return os.path.exists(tesseract_cmd)
    return shutil.which("tesseract") is not None


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not _integration_enabled(), reason="Set RUN_INTEGRATION=1 para habilitar")
def test_extract_text_from_native_pdf_reportlab():
    # Genera un PDF nativo con texto embebido (no escaneado)
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 20)
    c.drawString(72, 720, "DENUNCIA DE PRUEBA")
    c.drawString(72, 690, "Comisaria 1 - Capital")
    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()

    text = extract_text_from_pdf(pdf_bytes)

    assert "DENUNCIA" in text.upper()
    assert "COMISARIA" in text.upper()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.skipif(not _integration_enabled(), reason="Set RUN_INTEGRATION=1 para habilitar")
def test_ocr_pdf_bytes_scanned_pdf(tmp_path):
    # Genera un PDF tipo "escaneado" (imagen dentro de PDF), requiere Poppler + Tesseract.
    from PIL import Image, ImageDraw, ImageFont

    _tesseract_cmd, poppler_path = _configure_from_env()

    if not _has_poppler(poppler_path):
        pytest.skip("Poppler no detectado (definí POPPLER_PATH o agregá Poppler al PATH)")
    if not _has_tesseract(_tesseract_cmd):
        pytest.skip("Tesseract no detectado (definí TESSERACT_CMD o agregá Tesseract al PATH)")

    lang = os.getenv("TESSERACT_LANG", "eng").strip() or "eng"

    img = Image.new("RGB", (1600, 900), color="white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 64)
    except Exception:
        font = ImageFont.load_default()

    draw.multiline_text(
        (80, 120),
        "DENUNCIA DE PRUEBA\nComisaria 1 - Capital",
        fill="black",
        font=font,
        spacing=20,
    )

    buf = BytesIO()
    img.save(buf, format="PDF")
    pdf_bytes = buf.getvalue()

    text = ocr_pdf_bytes(pdf_bytes, poppler_path=poppler_path, lang=lang)

    # OCR puede variar según fuentes/instalación; verificamos señal mínima.
    assert isinstance(text, str)
    assert len(text.strip()) > 0
