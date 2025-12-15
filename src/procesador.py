from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from src.config_loader import AppConfig
from src.models.denuncia import DenunciaClasificada
from src.services.comisarias_repo import load_comisarias
from src.services.fuzzy_matcher import match_comisaria
from src.services.gemini_service import clasificar_denuncia, configure_gemini
from src.services.ocr_service import configure_tesseract, ocr_image_bytes, ocr_pdf_bytes
from src.services.pdf_service import extract_text_from_pdf
from src.services.file_router import build_destination
from src.services.stats_service import append_stats

logger = logging.getLogger(__name__)


def _parse_fecha(fecha: str | None) -> datetime | None:
    if not fecha:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(fecha.strip(), fmt)
        except Exception:
            continue
    return None


def procesar_archivo(
    repo_root: Path,
    cfg: AppConfig,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> tuple[str, DenunciaClasificada | None, str | None, Path | None]:
    """Devuelve: texto_extraido, denuncia_clasificada, motivo_revision, destino_final."""

    configure_tesseract(cfg.tesseract_cmd)

    # 1) Extraccion/OCR
    texto = ""
    if mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
        texto = extract_text_from_pdf(file_bytes)
        if len(texto) < 50:
            texto = ocr_pdf_bytes(file_bytes, poppler_path=cfg.poppler_path)
    else:
        texto = ocr_image_bytes(file_bytes)

    # Helpers para archivar + stats incluso en fallos
    def _write_and_stats(den: DenunciaClasificada | None, motivo: str) -> Path:
        now = datetime.now()
        year = now.year
        decision = build_destination(
            dest_root=cfg.dest_root,
            revision_root=cfg.revision_root,
            year=year,
            region=getattr(den, "region_asignada", None) if den else None,
            comisaria=getattr(den, "comisaria_asignada", None) if den else None,
            fecha_dt=_parse_fecha(getattr(den, "fecha", None)) if den else None,
            original_filename=filename,
            revision_motivo=motivo,
        )
        decision.dest_path.parent.mkdir(parents=True, exist_ok=True)
        decision.dest_path.write_bytes(file_bytes)

        stats_path = Path(cfg.stats_xlsx)
        if not stats_path.is_absolute():
            stats_path = repo_root / stats_path

        append_stats(
            stats_path,
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "fecha_denuncia": getattr(den, "fecha", None) if den else None,
                "region": getattr(den, "region_asignada", None) if den else None,
                "comisaria": getattr(den, "comisaria_asignada", None) if den else None,
                "tipo_delito": getattr(den, "tipo_delito", None) if den else None,
                "archivo_origen": filename,
                "archivo_destino": str(decision.dest_path),
                "status": decision.status,
                "motivo": decision.motivo,
            },
        )

        return decision.dest_path

    if not texto.strip():
        dest = _write_and_stats(None, "Denuncia ilegible o sin texto")
        return "", None, "Denuncia ilegible o sin texto", dest

    # 2) IA (Gemini)
    if not cfg.gemini_api_key:
        dest = _write_and_stats(None, "Falta GEMINI_API_KEY")
        return texto, None, "Falta GEMINI_API_KEY", dest

    configure_gemini(cfg.gemini_api_key)
    gem = clasificar_denuncia(texto, model_name=cfg.gemini_model)
    denuncia = gem.denuncia
    if not denuncia:
        dest = _write_and_stats(None, "La IA no devolvio JSON valido")
        return texto, None, "La IA no devolvio JSON valido", dest

    # 3) Match comisaria
    refs = load_comisarias(repo_root)
    match = match_comisaria(denuncia.comisaria_detectada, refs, threshold=cfg.fuzzy_threshold)

    motivo_revision = None
    if not denuncia.fecha:
        motivo_revision = "Falta de fecha"
    elif not match:
        motivo_revision = "Conflicto de jurisdiccion (baja similitud)"

    fecha_dt = _parse_fecha(denuncia.fecha)
    if denuncia.fecha and not fecha_dt:
        motivo_revision = motivo_revision or "Fecha con formato no reconocido"

    if match:
        denuncia = replace(
            denuncia,
            region_asignada=match.region,
            comisaria_asignada=match.comisaria,
            score_match=match.score,
        )

    year = (fecha_dt.year if fecha_dt else datetime.now().year)
    decision = build_destination(
        dest_root=cfg.dest_root,
        revision_root=cfg.revision_root,
        year=year,
        region=denuncia.region_asignada,
        comisaria=denuncia.comisaria_asignada,
        fecha_dt=fecha_dt,
        original_filename=filename,
        revision_motivo=motivo_revision,
    )

    # 4) Escribir archivo destino
    decision.dest_path.parent.mkdir(parents=True, exist_ok=True)
    decision.dest_path.write_bytes(file_bytes)

    # 5) Estadisticas
    stats_path = Path(cfg.stats_xlsx)
    if not stats_path.is_absolute():
        stats_path = repo_root / stats_path

    append_stats(
        stats_path,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "fecha_denuncia": denuncia.fecha,
            "region": denuncia.region_asignada,
            "comisaria": denuncia.comisaria_asignada,
            "tipo_delito": denuncia.tipo_delito,
            "archivo_origen": filename,
            "archivo_destino": str(decision.dest_path),
            "status": decision.status,
            "motivo": decision.motivo,
        },
    )

    return texto, denuncia, decision.motivo, decision.dest_path
