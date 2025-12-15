from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_MONTHS_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


@dataclass(frozen=True)
class RouteDecision:
    dest_path: Path
    status: str  # "OK" o "REVISION"
    motivo: str | None = None


def _month_folder(dt: datetime) -> str:
    mm = dt.month
    name = _MONTHS_ES.get(mm) or calendar.month_name[mm]
    return f"{mm:02d}_{name}"


def build_destination(
    dest_root: str,
    revision_root: str,
    year: int,
    region: str | None,
    comisaria: str | None,
    fecha_dt: datetime | None,
    original_filename: str,
    revision_motivo: str | None,
) -> RouteDecision:
    if revision_motivo or not (region and comisaria and fecha_dt):
        base = Path(revision_root)
        fname = original_filename
        if not fname.startswith("ERROR_"):
            fname = "ERROR_" + fname
        return RouteDecision(dest_path=base / fname, status="REVISION", motivo=revision_motivo or "Falta de datos")

    base = Path(dest_root) / str(year) / region / comisaria / _month_folder(fecha_dt)
    return RouteDecision(dest_path=base / original_filename, status="OK", motivo=None)
