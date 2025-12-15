from __future__ import annotations

import calendar
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

    base = Path(dest_root) / _year_folder(year) / region / comisaria / _month_folder(fecha_dt)
    return RouteDecision(dest_path=base / original_filename, status="OK", motivo=None)
