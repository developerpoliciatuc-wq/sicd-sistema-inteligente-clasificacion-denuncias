from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComisariaRef:
    region: str
    nombre: str


def load_comisarias(repo_root: Path) -> list[ComisariaRef]:
    path = repo_root / "config" / "comisarias.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    out: list[ComisariaRef] = []
    for item in data.get("comisarias", []):
        region = item.get("region")
        for nombre in item.get("lista", []):
            if region and nombre:
                out.append(ComisariaRef(region=region, nombre=nombre))
    return out
