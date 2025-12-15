from __future__ import annotations

import logging
from pathlib import Path

from src.config_loader import AppConfig


def setup_logging(repo_root: Path, cfg: AppConfig) -> None:
    log_path = Path(cfg.log_file)
    if not log_path.is_absolute():
        log_path = repo_root / log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, (cfg.log_level or "INFO").upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
