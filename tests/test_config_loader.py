from pathlib import Path

from src.config_loader import load_config


def test_load_config_env_overrides(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]

    monkeypatch.setenv("DEST_ROOT", "C:/tmp/OUT")
    monkeypatch.setenv("REVISION_ROOT", "C:/tmp/REV")
    monkeypatch.setenv("FUZZY_THRESHOLD", "90")
    monkeypatch.setenv("STATS_XLSX", "C:/tmp/stats.xlsx")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy")

    cfg = load_config(repo_root)

    assert cfg.dest_root == "C:/tmp/OUT"
    assert cfg.revision_root == "C:/tmp/REV"
    assert cfg.fuzzy_threshold == 90
    assert cfg.stats_xlsx == "C:/tmp/stats.xlsx"
    assert cfg.gemini_model == "gemini-test"
    assert cfg.gemini_api_key == "dummy"
