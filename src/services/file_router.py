from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_MONTHS_ES = {
    1: "ENERO",
    2: "FEBRERO",
    3: "MARZO",
    4: "ABRIL",
    5: "MAYO",
    6: "JUNIO",
    7: "JULIO",
    8: "AGOSTO",
    9: "SEPTIEMBRE",
    10: "OCTUBRE",
    11: "NOVIEMBRE",
    12: "DICIEMBRE",
}


@dataclass(frozen=True)
class RouteDecision:
    dest_path: Path
    status: str  # "OK" o "REVISION"
    motivo: str | None = None


def _month_folder(dt: datetime) -> str:
    mm = dt.month
    name = _MONTHS_ES.get(mm) or calendar.month_name[mm].upper()
    return f"{mm:02d} - {name}"


def _year_folder(year: int) -> str:
    return f"DENUNCIAS {year}"


def _sanitize_folder_name(name: str | None) -> str | None:
    """Sanitiza un nombre para usarlo como carpeta (remueve caracteres inválidos)."""
    if not name:
        return None
    # Reemplazar caracteres problemáticos para nombres de carpeta
    invalid_chars = '<>:"/\\|?*'
    result = name
    for char in invalid_chars:
        result = result.replace(char, '_')
    return result.strip()


def _format_modalidad_for_filename(modalidad: str | None, tipo_delito: str | None) -> str | None:
    """
    Formatea la modalidad para el nombre del archivo.
    Ej: ROBO_ARREBATO -> ARREBATO, HURTO_OPORTUNISTA -> OPORTUNISTA
    """
    if not modalidad:
        return None
    
    # Remover el prefijo del tipo de delito si existe
    if tipo_delito and modalidad.upper().startswith(tipo_delito.upper() + "_"):
        modalidad = modalidad[len(tipo_delito) + 1:]
    
    # Reemplazar guiones bajos por espacios para mejor legibilidad
    modalidad = modalidad.replace("_", " ")
    
    return modalidad.upper()


def _build_new_filename(original_filename: str, tipo_delito: str | None, modalidad_delito: str | None) -> str:
    """
    Construye el nuevo nombre de archivo incluyendo tipo y modalidad.
    Ej: D-563745-2025.pdf -> D-563745-2025 ROBO ARREBATO.pdf
    """
    if not tipo_delito:
        return original_filename
    
    # Obtener nombre base y extensión
    path = Path(original_filename)
    base_name = path.stem  # nombre sin extensión
    extension = path.suffix  # .pdf
    
    # Formatear modalidad (quitar prefijo del tipo)
    modalidad_formatted = _format_modalidad_for_filename(modalidad_delito, tipo_delito)
    
    # Construir nuevo nombre
    if modalidad_formatted:
        new_name = f"{base_name} {tipo_delito.upper()} {modalidad_formatted}{extension}"
    else:
        new_name = f"{base_name} {tipo_delito.upper()}{extension}"
    
    return new_name


def build_destination(
    dest_root: str,
    revision_root: str,
    year: int,
    region: str | None,
    comisaria: str | None,
    fecha_dt: datetime | None,
    original_filename: str,
    revision_motivo: str | None,
    tipo_delito: str | None = None,
    modalidad_delito: str | None = None,
) -> RouteDecision:
    if revision_motivo or not (region and comisaria and fecha_dt):
        base = Path(revision_root)
        fname = original_filename
        if not fname.startswith("ERROR_"):
            fname = "ERROR_" + fname
        return RouteDecision(dest_path=base / fname, status="REVISION", motivo=revision_motivo or "Falta de datos")

    # Construir ruta base: AÑO / REGION / COMISARIA / MES
    base = Path(dest_root) / _year_folder(year) / region / comisaria / _month_folder(fecha_dt)
    
    # Construir nuevo nombre de archivo con tipo y modalidad
    new_filename = _build_new_filename(original_filename, tipo_delito, modalidad_delito)
    
    return RouteDecision(dest_path=base / new_filename, status="OK", motivo=None)
