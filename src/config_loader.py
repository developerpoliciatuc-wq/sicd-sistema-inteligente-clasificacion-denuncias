from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    dest_root: str
    revision_root: str
    fuzzy_threshold: int
    stats_xlsx: str
    gemini_model: str

    tesseract_cmd: str | None = None
    poppler_path: str | None = None

    gemini_api_key: str | None = None

    log_level: str = "INFO"
    log_file: str = "logs/scid.log"


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config(repo_root: Path) -> AppConfig:
    cfg_path = repo_root / "config" / "config.json"
    raw = _read_json(cfg_path) if cfg_path.exists() else {}

    def env(name: str) -> str | None:
        value = os.getenv(name)
        return value if value and value.strip() else None

    dest_root = env("DEST_ROOT") or raw.get("dest_root") or r"\\ANALISIS-3\Analisis-3\MAPA DEL DELITO"
    revision_root = env("REVISION_ROOT") or raw.get("revision_root") or (dest_root.rstrip("\\") + r"\\_REVISION_MANUAL")

    fuzzy_threshold = int(env("FUZZY_THRESHOLD") or raw.get("fuzzy_threshold") or 85)
    stats_xlsx = env("STATS_XLSX") or raw.get("stats_xlsx") or "Base_Estadistica_2025.xlsx"
    gemini_model = env("GEMINI_MODEL") or raw.get("gemini_model") or "gemini-1.5-flash"

    return AppConfig(
        dest_root=dest_root,
        revision_root=revision_root,
        fuzzy_threshold=fuzzy_threshold,
        stats_xlsx=stats_xlsx,
        gemini_model=gemini_model,
        tesseract_cmd=env("TESSERACT_CMD"),
        poppler_path=env("POPPLER_PATH"),
        gemini_api_key=env("GEMINI_API_KEY"),
        log_level=env("LOG_LEVEL") or "INFO",
        log_file=env("LOG_FILE") or "logs/scid.log",
    )
