from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import google.generativeai as genai

from src.models.denuncia import (
    DenunciaClasificada, 
    DireccionHecho,
    DatosPersona,
    DatosVehiculo,
    DatosArma,
    ElementoSustraido,
    calcular_franja_horaria,
    derivar_mes_dia,
    NO_CONSTA,
)

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


def _normalizar_valor(valor: Any) -> str:
    """
    Normaliza un valor para el formulario QGIS.
    Convierte null/vacío a NO_CONSTA y asegura MAYÚSCULAS.
    """
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return NO_CONSTA
    return str(valor).strip().upper()


def _parsear_persona(data: dict | None, es_causante: bool = False) -> DatosPersona | None:
    """Parsea datos de persona desde el JSON de Gemini."""
    if not data or not isinstance(data, dict):
        return None
    
    # Si todos los valores son null, retornar None
    valores = [data.get(k) for k in ["apellido_nombre", "sexo", "edad", "dni", "direccion"]]
    if es_causante:
        valores.extend([data.get(k) for k in ["alias", "descripcion", "situacion"]])
    
    if not any(v for v in valores):
        return None
    
    return DatosPersona(
        apellido_nombre=_normalizar_valor(data.get("apellido_nombre")),
        sexo=_normalizar_valor(data.get("sexo")),
        edad=_normalizar_valor(data.get("edad")),
        dni=_normalizar_valor(data.get("dni")),
        direccion=_normalizar_valor(data.get("direccion")),
        alias=_normalizar_valor(data.get("alias")) if es_causante else None,
        descripcion=_normalizar_valor(data.get("descripcion")) if es_causante else None,
        situacion=_normalizar_valor(data.get("situacion")) if es_causante else None,
    )


def _postprocesar_denuncia(data: dict) -> tuple[DenunciaClasificada, str | None]:
    """
    Post-procesa los datos extraídos por Gemini.
    
    Retorna:
        - DenunciaClasificada con valores normalizados
        - motivo_revision si requiere revisión manual (ej: breve_resena > 254 chars)
    """
    motivo_revision = None
    requiere_revision = False
    
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
    
    # Parsear personas
    victima = _parsear_persona(data.get("victima"))
    denunciante = _parsear_persona(data.get("denunciante"))
    causante = _parsear_persona(data.get("causante"), es_causante=True)
    
    # Parsear vehículo
    vehiculo_data = data.get("vehiculo") or {}
    vehiculo = None
    if isinstance(vehiculo_data, dict) and any(vehiculo_data.values()):
        vehiculo = DatosVehiculo(
            tipo=_normalizar_valor(vehiculo_data.get("tipo")),
            descripcion=_normalizar_valor(vehiculo_data.get("descripcion")),
        )
    
    # Parsear arma
    arma_data = data.get("arma") or {}
    arma = None
    if isinstance(arma_data, dict) and any(arma_data.values()):
        arma = DatosArma(
            tipo=_normalizar_valor(arma_data.get("tipo")),
            detalle=_normalizar_valor(arma_data.get("detalle")),
        )
    
    # Parsear elemento sustraído
    elemento_data = data.get("elemento_sustraido") or {}
    elemento = None
    if isinstance(elemento_data, dict) and any(elemento_data.values()):
        elemento = ElementoSustraido(
            tipo=_normalizar_valor(elemento_data.get("tipo")),
            detalle=_normalizar_valor(elemento_data.get("detalle")),
        )
    
    # Procesar fecha y derivar mes/día
    fecha = data.get("fecha")
    mes, dia_semana = derivar_mes_dia(fecha)
    
    # Procesar hora y calcular franja horaria
    hora = data.get("hora")
    franja_horaria = calcular_franja_horaria(hora)
    
    # Obtener breve reseña (sin límite de caracteres)
    breve_resena = data.get("breve_resena")
    
    denuncia = DenunciaClasificada(
        # Identificación
        fecha=fecha,
        numero_sumario=_normalizar_valor(data.get("numero_sumario")),
        
        # Institucional
        comisaria_detectada=data.get("comisaria_detectada"),
        jurisdiccion=_normalizar_valor(data.get("jurisdiccion")),
        
        # Clasificación
        tipo_delito=data.get("tipo_delito"),
        modalidad_delito=data.get("modalidad_delito"),
        
        # Temporalidad
        hora=_normalizar_valor(hora),
        franja_horaria=franja_horaria,
        mes=mes,
        dia_semana=dia_semana,
        
        # Ubicación
        lugar=_normalizar_valor(data.get("lugar")),
        detalle_lugar=_normalizar_valor(data.get("detalle_lugar")),
        direccion_hecho=direccion_hecho,
        
        # Reseña
        breve_resena=_normalizar_valor(breve_resena) if breve_resena else NO_CONSTA,
        
        # Personas
        victima=victima,
        denunciante=denunciante,
        vinculo_denunciante_victima=_normalizar_valor(data.get("vinculo_denunciante_victima")),
        causante=causante,
        
        # Objetos
        vehiculo=vehiculo,
        arma=arma,
        elemento_sustraido=elemento,
        
        # Control
        requiere_revision_manual=requiere_revision,
        motivo_revision=motivo_revision,
    )
    
    return denuncia, motivo_revision


def clasificar_denuncia(texto: str, model_name: str) -> GeminiResult:
    """
    Clasifica una denuncia policial usando Gemini AI.
    
    Extrae TODOS los campos del formulario QGIS:
    - Datos del hecho (fecha, hora, lugar, delito, modalidad)
    - Datos de víctima, denunciante y causante
    - Vehículos, armas y elementos sustraídos
    - Breve reseña (máx 254 caracteres)
    
    Retorna GeminiResult con denuncia=None si falla.
    """
    
    modalidades_text = _build_prompt_modalidades()
    data = _load_modalidades()
    tipos_validos = data.get("tipos_delito", ["HURTO", "ROBO", "ESTAFA", "PORTACION_ARMA_FUEGO"])
    
    prompt = f"""Eres un experto en clasificación de denuncias policiales de Tucumán, Argentina.
Analiza el siguiente texto de denuncia y extrae TODA la información solicitada para completar el formulario policial.

INSTRUCCIONES GENERALES:
- TODAS las respuestas deben estar en MAYÚSCULAS
- Si un dato NO APARECE en el texto, usa null (el sistema lo convertirá a "NO CONSTA")
- Extrae EXACTAMENTE lo que dice el documento, no inventes datos

=== DATOS A EXTRAER ===

1. IDENTIFICACIÓN:
   - numero_sumario: Número de imagen, sumario o fecha de memorándum
   - fecha: Fecha del hecho en formato AAAA-MM-DD
   - hora: Hora del hecho en formato HH:MM (24 horas)

2. INSTITUCIÓN:
   - comisaria_detectada: Nombre de la comisaría/dependencia donde se realizó la denuncia
   - jurisdiccion: Jurisdicción donde tuvo lugar el delito

3. CLASIFICACIÓN DEL DELITO:
   - tipo_delito: Debe ser uno de {tipos_validos}
   - modalidad_delito: Modalidad específica según las definiciones abajo

4. UBICACIÓN DEL HECHO:
   - lugar: Tipo de lugar (VIA PUBLICA, DOMICILIO, COMERCIO, TRANSPORTE PUBLICO, ESTABLECIMIENTO EDUCATIVO, etc.)
   - detalle_lugar: Descripción específica del lugar
   - ubicacion_hecho: objeto con calle_principal, calle_secundaria, numero, barrio, localidad, referencia

5. RESEÑA:
   - breve_resena: Resumen del hecho con los detalles más relevantes. MÁXIMO 254 CARACTERES.

6. VEHÍCULOS:
   - vehiculo.tipo: Tipo de vehículo utilizado (MOTO, AUTO, BICICLETA, CAMIONETA, etc.)
   - vehiculo.descripcion: Descripción del vehículo (color, marca, patente si consta)

7. ARMAS:
   - arma.tipo: Tipo de arma (ARMA DE FUEGO, ARMA BLANCA, ELEMENTO CONTUNDENTE, etc.)
   - arma.detalle: Descripción del arma

8. ELEMENTO SUSTRAÍDO:
   - elemento_sustraido.tipo: Tipo de elemento (CELULAR, DINERO, CARTERA, MOCHILA, NOTEBOOK, ELECTRODOMESTICO, etc.)
   - elemento_sustraido.detalle: Descripción detallada de lo sustraído

9. DATOS DE LA VÍCTIMA:
   - victima.apellido_nombre: Apellido y nombre completo
   - victima.sexo: MASCULINO o FEMENINO
   - victima.edad: Edad en años
   - victima.dni: Número de DNI
   - victima.direccion: Dirección de domicilio

10. DATOS DEL DENUNCIANTE:
    - denunciante.apellido_nombre: Apellido y nombre completo
    - denunciante.sexo: MASCULINO o FEMENINO
    - denunciante.edad: Edad en años
    - denunciante.dni: Número de DNI
    - denunciante.direccion: Dirección de domicilio
    - vinculo_denunciante_victima: Relación con la víctima (EL MISMO, FAMILIAR, CONOCIDO, TESTIGO, etc.)

11. DATOS DEL CAUSANTE/IMPUTADO:
    - causante.apellido_nombre: Apellido y nombre (incluir "ALIAS [apodo]" si consta)
    - causante.sexo: MASCULINO o FEMENINO
    - causante.edad: Edad aproximada
    - causante.dni: Número de DNI si se conoce
    - causante.direccion: Dirección si se conoce
    - causante.alias: Apodo si consta
    - causante.descripcion: Descripción física o características
    - causante.situacion: APREHENDIDO, IDENTIFICADO, NO IDENTIFICADO, PROFUGO, etc.

{modalidades_text}

=== FORMATO DE RESPUESTA ===

Responde ÚNICAMENTE con un JSON válido (sin markdown, sin explicaciones):

{{
  "numero_sumario": "string o null",
  "fecha": "AAAA-MM-DD o null",
  "hora": "HH:MM o null",
  "comisaria_detectada": "string o null",
  "jurisdiccion": "string o null",
  "tipo_delito": "uno de {tipos_validos} o null",
  "modalidad_delito": "string o null",
  "lugar": "string o null",
  "detalle_lugar": "string o null",
  "ubicacion_hecho": {{
    "calle_principal": "string o null",
    "calle_secundaria": "string o null",
    "numero": "string o null",
    "barrio": "string o null",
    "localidad": "string o null",
    "referencia": "string o null"
  }},
  "breve_resena": "string MÁXIMO 254 CARACTERES o null",
  "vehiculo": {{
    "tipo": "string o null",
    "descripcion": "string o null"
  }},
  "arma": {{
    "tipo": "string o null",
    "detalle": "string o null"
  }},
  "elemento_sustraido": {{
    "tipo": "string o null",
    "detalle": "string o null"
  }},
  "victima": {{
    "apellido_nombre": "string o null",
    "sexo": "MASCULINO/FEMENINO o null",
    "edad": "string o null",
    "dni": "string o null",
    "direccion": "string o null"
  }},
  "denunciante": {{
    "apellido_nombre": "string o null",
    "sexo": "MASCULINO/FEMENINO o null",
    "edad": "string o null",
    "dni": "string o null",
    "direccion": "string o null"
  }},
  "vinculo_denunciante_victima": "string o null",
  "causante": {{
    "apellido_nombre": "string o null",
    "sexo": "MASCULINO/FEMENINO o null",
    "edad": "string o null",
    "dni": "string o null",
    "direccion": "string o null",
    "alias": "string o null",
    "descripcion": "string o null",
    "situacion": "string o null"
  }}
}}

=== TEXTO DE LA DENUNCIA ===

{texto}
"""

    max_retries = 3
    retry_delay = 15  # segundos
    
    for intento in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(prompt)
            raw = (resp.text or "").strip()

            data = _safe_json_loads(raw)
            if not isinstance(data, dict):
                return GeminiResult(raw_text=raw, denuncia=None)

            # Post-procesar datos (normalizar, calcular franja horaria, etc.)
            denuncia, motivo = _postprocesar_denuncia(data)
            
            return GeminiResult(raw_text=raw, denuncia=denuncia)
        except Exception as e:
            error_str = str(e)
            # Si es error de cuota (429), reintentar después de esperar
            if "429" in error_str or "ResourceExhausted" in error_str or "quota" in error_str.lower():
                if intento < max_retries - 1:
                    logger.warning(f"Cuota de Gemini excedida, reintentando en {retry_delay}s... (intento {intento + 1}/{max_retries})")
                    import time
                    time.sleep(retry_delay)
                    continue
            logger.exception("Fallo en Gemini API")
            return GeminiResult(raw_text="", denuncia=None)
    
    return GeminiResult(raw_text="", denuncia=None)
