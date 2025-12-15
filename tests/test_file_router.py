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


def test_build_destination_with_tipo_and_modalidad_delito(tmp_path: Path):
    """Verifica que tipo_delito y modalidad_delito se agregan al nombre del archivo."""
    dt = datetime(2025, 12, 15)
    decision = build_destination(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        year=2025,
        region="UNIDAD REGIONAL ESTE",
        comisaria="COLOMBRES",
        fecha_dt=dt,
        original_filename="D-563745-2025.pdf",
        revision_motivo=None,
        tipo_delito="ROBO",
        modalidad_delito="ROBO_ARREBATO",
    )

    assert decision.status == "OK"
    # Nombre debe ser: D-563745-2025 ROBO ARREBATO.pdf
    assert decision.dest_path.name == "D-563745-2025 ROBO ARREBATO.pdf"
    assert "DENUNCIAS 2025" in decision.dest_path.parts
    assert "12 - DICIEMBRE" in decision.dest_path.parts


def test_build_destination_with_only_tipo_delito(tmp_path: Path):
    """Verifica que solo tipo_delito (sin modalidad) se agrega al nombre."""
    dt = datetime(2025, 12, 15)
    decision = build_destination(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        year=2025,
        region="UNIDAD REGIONAL ESTE",
        comisaria="COLOMBRES",
        fecha_dt=dt,
        original_filename="D-563745-2025.pdf",
        revision_motivo=None,
        tipo_delito="ROBO",
        modalidad_delito=None,
    )

    assert decision.status == "OK"
    # Nombre debe ser: D-563745-2025 ROBO.pdf
    assert decision.dest_path.name == "D-563745-2025 ROBO.pdf"


def test_build_destination_hurto_oportunista(tmp_path: Path):
    """Verifica formato correcto para HURTO OPORTUNISTA."""
    dt = datetime(2025, 12, 15)
    decision = build_destination(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        year=2025,
        region="UNIDAD REGIONAL ESTE",
        comisaria="COLOMBRES",
        fecha_dt=dt,
        original_filename="D-563414-2025.pdf",
        revision_motivo=None,
        tipo_delito="HURTO",
        modalidad_delito="HURTO_OPORTUNISTA",
    )

    assert decision.status == "OK"
    assert decision.dest_path.name == "D-563414-2025 HURTO OPORTUNISTA.pdf"


def test_build_destination_estafa(tmp_path: Path):
    """Verifica formato correcto para ESTAFA TELEFONICA."""
    dt = datetime(2025, 12, 15)
    decision = build_destination(
        dest_root=str(tmp_path / "OUT"),
        revision_root=str(tmp_path / "REV"),
        year=2025,
        region="UNIDAD REGIONAL ESTE",
        comisaria="COLOMBRES",
        fecha_dt=dt,
        original_filename="D-566003-2025.pdf",
        revision_motivo=None,
        tipo_delito="ESTAFA",
        modalidad_delito="ESTAFA_TELEFONICA",
    )

    assert decision.status == "OK"
    assert decision.dest_path.name == "D-566003-2025 ESTAFA TELEFONICA.pdf"
