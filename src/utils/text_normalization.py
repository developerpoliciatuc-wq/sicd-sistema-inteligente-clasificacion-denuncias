from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_text(text: str) -> str:
    if not text:
        return ""

    t = text.strip().lower()
    t = strip_accents(t)

    # Normalizaciones comunes (sin inventar colores/UX, solo texto)
    t = t.replace("comisaria", "cria")
    t = t.replace("comisaría", "cria")
    t = t.replace("cria.", "cria")
    t = t.replace("sub. cria.", "sub cria")
    t = t.replace("sub. cria", "sub cria")
    t = t.replace("subcria", "sub cria")

    # Quitar caracteres raros y normalizar espacios
    t = _NON_ALNUM_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t
