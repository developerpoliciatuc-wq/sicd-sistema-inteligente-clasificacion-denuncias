from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai

from src.models.denuncia import DenunciaClasificada

logger = logging.getLogger(__name__)


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


@dataclass(frozen=True)
class GeminiResult:
    raw_text: str
    denuncia: DenunciaClasificada | None


def configure_gemini(api_key: str | None) -> None:
    if api_key and api_key.strip():
        genai.configure(api_key=api_key)


def _safe_json_loads(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    m = _JSON_BLOCK_RE.search(text)
    payload = m.group(0) if m else text
    try:
        return json.loads(payload)
    except Exception:
        return None


def clasificar_denuncia(texto: str, model_name: str) -> GeminiResult:
    """Devuelve fecha, comisaria_detectada y tipo_delito. Si falla, denuncia=None."""
    prompt = (
        "Extrae datos de una denuncia policial de Tucuman. "
        "Responde SOLO con JSON valido sin markdown. "
        "Claves exactas: fecha, comisaria_detectada, tipo_delito. "
        "fecha en formato AAAA-MM-DD si es posible; si no, null. "
        "Si no hay datos, usa null.\n\n"
        "TEXTO_DENUNCIA:\n" + texto
    )

    try:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(prompt)
        raw = (resp.text or "").strip()

        data = _safe_json_loads(raw)
        if not isinstance(data, dict):
            return GeminiResult(raw_text=raw, denuncia=None)

        denuncia = DenunciaClasificada(
            fecha=data.get("fecha"),
            comisaria_detectada=data.get("comisaria_detectada"),
            tipo_delito=data.get("tipo_delito"),
        )
        return GeminiResult(raw_text=raw, denuncia=denuncia)
    except Exception:
        logger.exception("Fallo en Gemini API")
        return GeminiResult(raw_text="", denuncia=None)
