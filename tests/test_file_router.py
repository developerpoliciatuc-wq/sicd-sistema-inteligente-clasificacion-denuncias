from datetime import datetime
from pathlib import Path

from src.services.file_router import build_destination


def test_build_destination_revision_prefixes_error_filename(tmp_path: Path):
    decision = build_destination(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        year=2025,
        region=None,
        comisaria=None,
        fecha_dt=None,
        original_filename="denuncia.pdf",
        revision_motivo=None,
    )

    assert decision.status == "REVISION"
    assert decision.dest_path.name == "ERROR_denuncia.pdf"
    assert str(decision.dest_path).startswith(str(tmp_path / "REV"))


def test_build_destination_ok_includes_month_folder_es(tmp_path: Path):
    dt = datetime(2025, 12, 15)
    decision = build_destination(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        year=2025,
        region="UNIDAD REGIONAL ESTE",
        comisaria="COLOMBRES",
        fecha_dt=dt,
        original_filename="denuncia.pdf",
        revision_motivo=None,
    )

    assert decision.status == "OK"
    # .../DENUNCIAS 2025/UNIDAD REGIONAL ESTE/COLOMBRES/12 - DICIEMBRE/denuncia.pdf
    assert "DENUNCIAS 2025" in decision.dest_path.parts
    assert "12 - DICIEMBRE" in decision.dest_path.parts
    assert decision.dest_path.name == "denuncia.pdf"
