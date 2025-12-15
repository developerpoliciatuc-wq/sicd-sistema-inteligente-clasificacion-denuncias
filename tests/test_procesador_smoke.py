from pathlib import Path

from src.config_loader import AppConfig
from src.models.denuncia import DenunciaClasificada
from src.services.comisarias_repo import ComisariaRef
from src.services.fuzzy_matcher import MatchResult
from src.services.gemini_service import GeminiResult

import src.procesador as procesador


def _cfg(tmp_path: Path, gemini_api_key: str | None) -> AppConfig:
    return AppConfig(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        fuzzy_threshold=85,
        stats_xlsx=str(tmp_path / "stats.xlsx"),
        gemini_model="dummy-model",
        gemini_api_key=gemini_api_key,
        tesseract_cmd=None,
        poppler_path=None,
    )


def test_procesar_archivo_missing_api_key_goes_to_revision(monkeypatch, tmp_path: Path):
    cfg = _cfg(tmp_path, gemini_api_key=None)

    monkeypatch.setattr(procesador, "extract_text_from_pdf", lambda _b: "x" * 60)

    texto, denuncia, motivo, destino = procesador.procesar_archivo(
        repo_root=tmp_path,
        cfg=cfg,
        file_bytes=b"%PDF-1.4 dummy",
        filename="a.pdf",
        mime_type="application/pdf",
    )

    assert texto.strip()
    assert denuncia is None
    assert motivo == "Falta GEMINI_API_KEY"
    assert destino is not None
    assert destino.exists()
    assert destino.name.startswith("ERROR_")
    assert str(destino).startswith(str(tmp_path / "REV"))
    assert (tmp_path / "stats.xlsx").exists()


def test_procesar_archivo_happy_path_routes_ok(monkeypatch, tmp_path: Path):
    cfg = _cfg(tmp_path, gemini_api_key="dummy")

    monkeypatch.setattr(procesador, "extract_text_from_pdf", lambda _b: "x" * 60)

    dummy_den = DenunciaClasificada(
        fecha="2025-12-15",
        comisaria_detectada="Comisaria 1",
        tipo_delito="ROBO",
    )
    monkeypatch.setattr(
        procesador,
        "clasificar_denuncia",
        lambda _t, model_name: GeminiResult(raw_text="{}", denuncia=dummy_den),
    )
    monkeypatch.setattr(
        procesador,
        "load_comisarias",
        lambda _root: [ComisariaRef(region="R1", nombre="Cria 1")],
    )
    monkeypatch.setattr(
        procesador,
        "match_comisaria",
        lambda _txt, _refs, threshold: MatchResult(region="R1", comisaria="Cria 1", score=99.0),
    )

    texto, denuncia, motivo, destino = procesador.procesar_archivo(
        repo_root=tmp_path,
        cfg=cfg,
        file_bytes=b"%PDF-1.4 dummy",
        filename="b.pdf",
        mime_type="application/pdf",
    )

    assert texto.strip()
    assert denuncia is not None
    assert motivo is None
    assert destino is not None and destino.exists()
    assert str(destino).startswith(str(tmp_path / "OUT"))
    assert "12 - DICIEMBRE" in destino.parts
    assert (tmp_path / "stats.xlsx").exists()
