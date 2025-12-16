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
from src.services.geocoding_service import get_geocoding_service
from src.services.qgis_sync_service import QGISSyncService

# Servicio de sincronización QGIS (singleton)
_qgis_sync_service: QGISSyncService | None = None


def get_qgis_sync_service(repo_root: Path) -> QGISSyncService:
    """Obtiene o crea el servicio de sincronización QGIS."""
    global _qgis_sync_service
    if _qgis_sync_service is None:
        ruta_sync = repo_root / "data" / "OUTPUT" / "QGIS_SYNC"
        _qgis_sync_service = QGISSyncService(str(ruta_sync))
    return _qgis_sync_service

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
            tipo_delito=getattr(den, "tipo_delito", None) if den else None,
            modalidad_delito=getattr(den, "modalidad_delito", None) if den else None,
        )
        decision.dest_path.parent.mkdir(parents=True, exist_ok=True)
        decision.dest_path.write_bytes(file_bytes)

        stats_path = Path(cfg.stats_xlsx)
        if not stats_path.is_absolute():
            stats_path = repo_root / stats_path

        # Extraer datos de coordenadas si existen
        coords = getattr(den, "coordenadas", None) if den else None
        direccion = getattr(den, "direccion_hecho", None) if den else None
        
        append_stats(
            stats_path,
            {
                "timestamp": now.isoformat(timespec="seconds"),
                "fecha_denuncia": getattr(den, "fecha", None) if den else None,
                "region": getattr(den, "region_asignada", None) if den else None,
                "comisaria": getattr(den, "comisaria_asignada", None) if den else None,
                "tipo_delito": getattr(den, "tipo_delito", None) if den else None,
                "modalidad_delito": getattr(den, "modalidad_delito", None) if den else None,
                "direccion_hecho": direccion.to_query() if direccion else None,
                "latitud": coords.latitud if coords else None,
                "longitud": coords.longitud if coords else None,
                "precision_geo": coords.precision if coords else None,
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
    elif not denuncia.tipo_delito:
        motivo_revision = "Tipo de delito no determinado"
    elif not denuncia.modalidad_delito:
        motivo_revision = "Modalidad de delito no determinada"

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

    # 4) Geocodificación del lugar del hecho
    if denuncia.direccion_hecho:
        try:
            geocoding_service = get_geocoding_service()
            coordenadas = geocoding_service.geocodificar_con_fallback(denuncia.direccion_hecho)
            if coordenadas:
                denuncia = replace(denuncia, coordenadas=coordenadas)
                logger.info(f"Geocodificación exitosa: ({coordenadas.latitud}, {coordenadas.longitud})")
            else:
                logger.warning("No se pudo geocodificar la dirección del hecho")
        except Exception as e:
            logger.error(f"Error en geocodificación: {e}")

    # 4.1) Verificar si requiere revisión manual por breve_resena > 254 chars
    if denuncia.requiere_revision_manual:
        motivo_revision = motivo_revision or denuncia.motivo_revision
        logger.warning(f"Denuncia requiere revisión manual: {denuncia.motivo_revision}")

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
        tipo_delito=denuncia.tipo_delito,
        modalidad_delito=denuncia.modalidad_delito,
    )

    # 4) Escribir archivo destino
    decision.dest_path.parent.mkdir(parents=True, exist_ok=True)
    decision.dest_path.write_bytes(file_bytes)

    # 5) Estadisticas
    stats_path = Path(cfg.stats_xlsx)
    if not stats_path.is_absolute():
        stats_path = repo_root / stats_path

    # Extraer datos de coordenadas
    coords = denuncia.coordenadas
    direccion = denuncia.direccion_hecho
    
    append_stats(
        stats_path,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "fecha_denuncia": denuncia.fecha,
            "region": denuncia.region_asignada,
            "comisaria": denuncia.comisaria_asignada,
            "tipo_delito": denuncia.tipo_delito,
            "modalidad_delito": denuncia.modalidad_delito,
            "direccion_hecho": direccion.to_query() if direccion else None,
            "latitud": coords.latitud if coords else None,
            "longitud": coords.longitud if coords else None,
            "precision_geo": coords.precision if coords else None,
            "archivo_origen": filename,
            "archivo_destino": str(decision.dest_path),
            "status": decision.status,
            "motivo": decision.motivo,
        },
    )

    # 6) Sincronización con QGIS (si hay coordenadas)
    if denuncia.coordenadas:
        try:
            qgis_service = get_qgis_sync_service(repo_root)
            # Extraer número de denuncia del nombre del archivo
            numero_denuncia = filename.rsplit('.', 1)[0]  # Quitar extensión
            
            # Extraer datos de personas para el formulario QGIS
            victima = denuncia.victima
            denunciante = denuncia.denunciante
            causante = denuncia.causante
            vehiculo = denuncia.vehiculo
            arma = denuncia.arma
            elemento = denuncia.elemento_sustraido
            
            qgis_service.agregar_denuncia(
                numero_denuncia=numero_denuncia,
                latitud=denuncia.coordenadas.latitud,
                longitud=denuncia.coordenadas.longitud,
                tipo_delito=denuncia.tipo_delito or "DESCONOCIDO",
                modalidad=denuncia.modalidad_delito or "",
                comisaria=denuncia.comisaria_asignada or denuncia.comisaria_detectada or "",
                fecha_hecho=denuncia.fecha or "",
                direccion=denuncia.direccion_hecho.to_query() if denuncia.direccion_hecho else "",
                
                # Nuevos campos del formulario
                numero_sumario=denuncia.numero_sumario,
                jurisdiccion=denuncia.jurisdiccion,
                mes=denuncia.mes,
                dia_semana=denuncia.dia_semana,
                hora=denuncia.hora,
                franja_horaria=denuncia.franja_horaria,
                lugar=denuncia.lugar,
                detalle_lugar=denuncia.detalle_lugar,
                breve_resena=denuncia.breve_resena,
                
                # Vehículos
                vehiculo_utilizado=vehiculo.tipo if vehiculo else None,
                vehiculo_descripcion=vehiculo.descripcion if vehiculo else None,
                
                # Armas
                arma_utilizada=arma.tipo if arma else None,
                arma_detalle=arma.detalle if arma else None,
                
                # Elementos sustraídos
                elemento_sustraido=elemento.tipo if elemento else None,
                elemento_detalle=elemento.detalle if elemento else None,
                
                # Víctima
                victima_nombre=victima.apellido_nombre if victima else None,
                victima_sexo=victima.sexo if victima else None,
                victima_edad=victima.edad if victima else None,
                victima_dni=victima.dni if victima else None,
                victima_direccion=victima.direccion if victima else None,
                
                # Denunciante
                denunciante_nombre=denunciante.apellido_nombre if denunciante else None,
                denunciante_sexo=denunciante.sexo if denunciante else None,
                denunciante_edad=denunciante.edad if denunciante else None,
                denunciante_dni=denunciante.dni if denunciante else None,
                denunciante_direccion=denunciante.direccion if denunciante else None,
                vinculo_denunciante_victima=denuncia.vinculo_denunciante_victima,
                
                # Causante
                causante_nombre=causante.apellido_nombre if causante else None,
                causante_sexo=causante.sexo if causante else None,
                causante_edad=causante.edad if causante else None,
                causante_dni=causante.dni if causante else None,
                causante_direccion=causante.direccion if causante else None,
                causante_descripcion=causante.descripcion if causante else None,
                causante_situacion=causante.situacion if causante else None,
                
                # Control
                requiere_revision=denuncia.requiere_revision_manual,
                motivo_revision=denuncia.motivo_revision if denuncia.requiere_revision_manual else None,
            )
            logger.info(f"Denuncia sincronizada con QGIS: {numero_denuncia}")
        except Exception as e:
            logger.error(f"Error sincronizando con QGIS: {e}")

    return texto, denuncia, decision.motivo, decision.dest_path
