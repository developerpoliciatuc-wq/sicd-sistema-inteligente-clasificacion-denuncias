from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import google.generativeai as genai

from src.models.denuncia import DenunciaClasificada, DireccionHecho

logger = logging.getLogger(__name__)


_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")

# Cache para las modalidades cargadas
_MODALIDADES_CACHE: dict[str, Any] | None = None


@dataclass(frozen=True)
class GeminiResult:
    raw_text: str
    denuncia: DenunciaClasificada | None


def configure_gemini(api_key: str | None) -> None:
    if api_key and api_key.strip():
        genai.configure(api_key=api_key)


def _load_modalidades(config_path: Path | None = None) -> dict[str, Any]:
    """Carga las modalidades de delitos desde el archivo JSON."""
    global _MODALIDADES_CACHE
    if _MODALIDADES_CACHE is not None:
        return _MODALIDADES_CACHE
    
    if config_path is None:
        # Buscar en ubicaciones estándar
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "modalidades_delitos.json",
            Path("config/modalidades_delitos.json"),
        ]
        for p in possible_paths:
            if p.exists():
                config_path = p
                break
    
    if config_path is None or not config_path.exists():
        logger.warning("No se encontró archivo de modalidades, usando valores por defecto")
        return {"tipos_delito": [], "modalidades": {}, "definiciones_generales": {}}
    
    with open(config_path, "r", encoding="utf-8") as f:
        _MODALIDADES_CACHE = json.load(f)
    return _MODALIDADES_CACHE


def _build_prompt_modalidades() -> str:
    """Construye el texto del prompt con todas las definiciones de modalidades."""
    data = _load_modalidades()
    
    lines = []
    lines.append("=== TIPOS DE DELITO Y SUS MODALIDADES ===\n")
    
    # Definiciones generales
    for tipo in data.get("tipos_delito", []):
        def_general = data.get("definiciones_generales", {}).get(tipo, "")
        lines.append(f"## {tipo}")
        if def_general:
            lines.append(f"DEFINICIÓN: {def_general}\n")
        
        # Modalidades específicas
        modalidades = data.get("modalidades", {}).get(tipo, {})
        for modalidad, descripcion in modalidades.items():
            lines.append(f"  - {modalidad}: {descripcion}")
        lines.append("")
    
    return "\n".join(lines)


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
    """Devuelve fecha, comisaria_detectada, tipo_delito, modalidad_delito y ubicacion_hecho. Si falla, denuncia=None."""
    
    modalidades_text = _build_prompt_modalidades()
    data = _load_modalidades()
    tipos_validos = data.get("tipos_delito", ["HURTO", "ROBO", "ESTAFA", "PORTACION_ARMA_FUEGO"])
    
    prompt = f"""Eres un experto en clasificación de denuncias policiales de Tucumán, Argentina.
Analiza el siguiente texto de denuncia y extrae la información solicitada.

INSTRUCCIONES:
1. Extrae la FECHA del hecho en formato AAAA-MM-DD
2. Identifica la COMISARÍA donde se realizó la denuncia
3. Clasifica el TIPO DE DELITO: debe ser uno de {tipos_validos}
4. Determina la MODALIDAD específica del delito basándote en el RELATO DEL HECHO
5. IMPORTANTE: Extrae la UBICACIÓN DONDE OCURRIÓ EL HECHO del "RELATO DEL HECHO"

PARA LA UBICACIÓN, busca en el relato:
- Calles mencionadas (ej: "CALLE MITRE", "AV. ALEM", "AVENIDA SARMIENTO")
- Intersecciones (ej: "MITRE Y MATIENZO", "ESQUINA DE...", "Y" entre dos calles)
- Números de calle (ej: "Av. Alem 450", "calle 25 de Mayo 1200")
- Barrios (ej: "Barrio Norte", "Villa Luján", "Ciudadela")
- Localidades de Tucumán (ej: "Lules", "Yerba Buena", "Tafí Viejo", "San Miguel de Tucumán")
- Referencias (ej: "frente a la plaza", "cerca del hospital", "al lado de...")

IMPORTANTE: 
- Analiza cuidadosamente el "RELATO DEL HECHO" para determinar la modalidad correcta
- La modalidad debe coincidir EXACTAMENTE con una de las opciones listadas abajo
- Si no puedes determinar la modalidad con certeza, usa null
- Para la ubicación, extrae TODOS los datos que puedas encontrar en el relato

{modalidades_text}

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin explicaciones).
Claves exactas requeridas:
{{
  "fecha": "AAAA-MM-DD o null",
  "comisaria_detectada": "nombre de comisaría o null",
  "tipo_delito": "uno de {tipos_validos} o null",
  "modalidad_delito": "modalidad específica o null",
  "ubicacion_hecho": {{
    "calle_principal": "nombre de la calle principal o null",
    "calle_secundaria": "calle de intersección (si hay) o null",
    "numero": "número de la dirección o null",
    "barrio": "nombre del barrio o null",
    "localidad": "ciudad/pueblo de Tucumán o null",
    "referencia": "punto de referencia mencionado o null"
  }}
}}

TEXTO DE LA DENUNCIA:
{texto}
"""

    try:
        model = genai.GenerativeModel(model_name)
        resp = model.generate_content(prompt)
        raw = (resp.text or "").strip()

        data = _safe_json_loads(raw)
        if not isinstance(data, dict):
            return GeminiResult(raw_text=raw, denuncia=None)

        # Parsear ubicación del hecho
        ubicacion_data = data.get("ubicacion_hecho") or {}
        direccion_hecho = None
        if isinstance(ubicacion_data, dict) and any(ubicacion_data.values()):
            direccion_hecho = DireccionHecho(
                calle_principal=ubicacion_data.get("calle_principal"),
                calle_secundaria=ubicacion_data.get("calle_secundaria"),
                numero=ubicacion_data.get("numero"),
                barrio=ubicacion_data.get("barrio"),
                localidad=ubicacion_data.get("localidad"),
                referencia=ubicacion_data.get("referencia"),
            )

        denuncia = DenunciaClasificada(
            fecha=data.get("fecha"),
            comisaria_detectada=data.get("comisaria_detectada"),
            tipo_delito=data.get("tipo_delito"),
            modalidad_delito=data.get("modalidad_delito"),
            direccion_hecho=direccion_hecho,
        )
        return GeminiResult(raw_text=raw, denuncia=denuncia)
    except Exception:
        logger.exception("Fallo en Gemini API")
        return GeminiResult(raw_text="", denuncia=None)
