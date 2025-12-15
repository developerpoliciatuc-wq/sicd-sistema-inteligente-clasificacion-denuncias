from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DenunciaClasificada:
    fecha: Optional[str]
    comisaria_detectada: Optional[str]
    tipo_delito: Optional[str]

    region_asignada: Optional[str] = None
    comisaria_asignada: Optional[str] = None
    score_match: Optional[float] = None

    motivo_revision: Optional[str] = None
