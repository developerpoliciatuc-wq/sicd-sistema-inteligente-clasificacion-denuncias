from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from src.services.comisarias_repo import ComisariaRef
from src.utils.text_normalization import normalize_text


@dataclass(frozen=True)
class MatchResult:
    region: str
    comisaria: str
    score: float


def match_comisaria(texto_detectado: str | None, comisarias: list[ComisariaRef], threshold: int) -> MatchResult | None:
    if not texto_detectado or not texto_detectado.strip():
        return None

    choices = [c.nombre for c in comisarias]

    # RapidFuzz permite un preprocesado; usamos nuestra normalizacion
    def _processor(s: str) -> str:
        return normalize_text(s)

    best = process.extractOne(
        query=texto_detectado,
        choices=choices,
        scorer=fuzz.WRatio,
        processor=_processor,
    )

    if not best:
        return None

    name, score, idx = best
    if score < threshold:
        return None

    ref = comisarias[idx]
    return MatchResult(region=ref.region, comisaria=ref.nombre, score=float(score))
