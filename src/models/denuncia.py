from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DireccionHecho:
    """Datos de ubicación extraídos del relato del hecho."""
    calle_principal: Optional[str] = None
    calle_secundaria: Optional[str] = None  # Para intersecciones
    numero: Optional[str] = None
    barrio: Optional[str] = None
    localidad: Optional[str] = None
    referencia: Optional[str] = None
    
    def to_query(self) -> str:
        """Construye una query para geocodificación."""
        parts = []
        if self.calle_principal:
            if self.numero:
                parts.append(f"{self.calle_principal} {self.numero}")
            elif self.calle_secundaria:
                parts.append(f"{self.calle_principal} y {self.calle_secundaria}")
            else:
                parts.append(self.calle_principal)
        if self.barrio:
            parts.append(self.barrio)
        if self.localidad:
            parts.append(self.localidad)
        else:
            parts.append("Tucumán")
        parts.append("Argentina")
        return ", ".join(parts)


@dataclass(frozen=True)
class Coordenadas:
    """Coordenadas geográficas del lugar del hecho."""
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    precision: Optional[str] = None  # "exacta", "aproximada", "barrio", "localidad"
    fuente: Optional[str] = None  # "nominatim", "manual", etc.


@dataclass(frozen=True)
class DenunciaClasificada:
    fecha: Optional[str]
    comisaria_detectada: Optional[str]
    tipo_delito: Optional[str]
    modalidad_delito: Optional[str] = None

    region_asignada: Optional[str] = None
    comisaria_asignada: Optional[str] = None
    score_match: Optional[float] = None

    motivo_revision: Optional[str] = None
    
    # Campos de georreferenciación
    direccion_hecho: Optional[DireccionHecho] = None
    coordenadas: Optional[Coordenadas] = None
