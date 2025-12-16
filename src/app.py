from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.config_loader import load_config
from src.procesador import procesar_archivo, get_qgis_sync_service
from src.utils.logging_setup import setup_logging

# Importaciones para el mapa
try:
    from streamlit_folium import st_folium
    from src.services.map_service import crear_mapa_denuncia
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

# Importación del servicio de jurisdicción
try:
    from src.services.jurisdiccion_service import JurisdiccionService
    JURISDICCION_AVAILABLE = True
except ImportError:
    JURISDICCION_AVAILABLE = False


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")

    cfg = load_config(repo_root)
    setup_logging(repo_root, cfg)

    st.set_page_config(page_title="SCID", layout="wide")
    st.title("Sistema de Clasificación Inteligente de Denuncias (SCID)")

    # Sidebar con panel de sincronización QGIS
    with st.sidebar:
        st.header("🗺️ Sincronización QGIS")
        
        qgis_service = get_qgis_sync_service(repo_root)
        stats = qgis_service.obtener_estadisticas()
        
        st.metric("Denuncias activas", stats["total_denuncias"])
        
        # Estadísticas por tipo de delito
        if stats["por_tipo_delito"]:
            st.write("**Por tipo de delito:**")
            for tipo, cantidad in stats["por_tipo_delito"].items():
                color = {"HURTO": "🔵", "ROBO": "🔴", "ESTAFA": "🟠", "PORTACION_ARMA_FUEGO": "⚫"}.get(tipo, "⚪")
                st.write(f"{color} {tipo}: {cantidad}")
        
        st.divider()
        
        # Ruta del archivo GeoJSON
        st.write("**Archivo GeoJSON:**")
        st.code(qgis_service.obtener_ruta_archivo_activo(), language=None)
        
        st.divider()
        
        # Botón de archivo histórico
        st.write("**Archivar denuncias:**")
        if st.button("📦 Archivar en histórico", help="Mueve todas las denuncias activas al histórico"):
            if stats["total_denuncias"] > 0:
                ruta_archivo = qgis_service.archivar_historico()
                st.success(f"Archivado: {ruta_archivo}")
                st.rerun()
            else:
                st.warning("No hay denuncias para archivar")
        
        # Lista de archivos históricos
        archivos = qgis_service.listar_archivos_historicos()
        if archivos:
            st.write("**Archivos históricos:**")
            for archivo in archivos[:5]:  # Mostrar últimos 5
                st.caption(f"📄 {archivo['nombre']}")
        
        st.divider()
        
        # Estado del servicio de jurisdicción
        if JURISDICCION_AVAILABLE:
            st.write("**Validación de jurisdicción:**")
            try:
                jurisdiccion_service = JurisdiccionService()
                info = jurisdiccion_service.obtener_info_estado()
                if info["servicio_operativo"]:
                    st.success("✅ Operativo")
                else:
                    if not info["geopandas_disponible"]:
                        st.warning("⚠️ geopandas no instalado")
                    elif not info["unidad_red_disponible"]:
                        st.warning(f"⚠️ Red Z: no disponible")
            except Exception as e:
                st.error(f"Error: {e}")

    # Panel principal
    st.caption("Carga una denuncia (PDF/Imagen). El sistema extrae texto, clasifica y archiva.")

    # Inicializar session_state para persistir resultados
    if "resultado_procesado" not in st.session_state:
        st.session_state.resultado_procesado = None
    if "archivo_actual" not in st.session_state:
        st.session_state.archivo_actual = None

    uploaded = st.file_uploader("Denuncia", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=False)

    if uploaded is None:
        st.info("Esperando archivo…")
        # Limpiar resultados anteriores si no hay archivo
        st.session_state.resultado_procesado = None
        st.session_state.archivo_actual = None
        return

    st.write(f"Archivo: {uploaded.name} ({uploaded.type})")

    # Detectar si cambió el archivo
    if st.session_state.archivo_actual != uploaded.name:
        st.session_state.resultado_procesado = None
        st.session_state.archivo_actual = uploaded.name

    if st.button("Procesar y archivar"):
        file_bytes = uploaded.getvalue()

        with st.spinner("Procesando…"):
            texto, denuncia, motivo, destino = procesar_archivo(
                repo_root=repo_root,
                cfg=cfg,
                file_bytes=file_bytes,
                filename=uploaded.name,
                mime_type=uploaded.type or "",
            )
        
        # Guardar resultado en session_state
        st.session_state.resultado_procesado = {
            "texto": texto,
            "denuncia": denuncia,
            "motivo": motivo,
            "destino": destino
        }

    # Mostrar resultados si existen (ya sea recién procesados o de session_state)
    if st.session_state.resultado_procesado:
        resultado = st.session_state.resultado_procesado
        texto = resultado["texto"]
        denuncia = resultado["denuncia"]
        motivo = resultado["motivo"]
        destino = resultado["destino"]

        st.subheader("Texto extraído")
        st.text_area("", value=texto[:20000], height=240)

        st.subheader("Resultado")
        if denuncia is None:
            st.error(f"No se pudo clasificar. Motivo: {motivo or 'Desconocido'}")
        else:
            # Datos principales de clasificación
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Clasificación:**")
                st.write(
                    {
                        "fecha": denuncia.fecha,
                        "comisaria_detectada": denuncia.comisaria_detectada,
                        "tipo_delito": denuncia.tipo_delito,
                        "modalidad_delito": denuncia.modalidad_delito,
                        "region_asignada": denuncia.region_asignada,
                        "comisaria_asignada": denuncia.comisaria_asignada,
                        "score_match": denuncia.score_match,
                    }
                )
            
            with col2:
                st.write("**Ubicación del hecho:**")
                if denuncia.direccion_hecho:
                    dir_hecho = denuncia.direccion_hecho
                    ubicacion_info = {
                        "calle_principal": dir_hecho.calle_principal,
                        "calle_secundaria": dir_hecho.calle_secundaria,
                        "numero": dir_hecho.numero,
                        "barrio": dir_hecho.barrio,
                        "localidad": dir_hecho.localidad,
                        "referencia": dir_hecho.referencia,
                    }
                    # Filtrar valores None
                    ubicacion_info = {k: v for k, v in ubicacion_info.items() if v}
                    st.write(ubicacion_info)
                else:
                    st.info("No se detectó ubicación del hecho")

            # Mapa de georreferenciación
            if denuncia.coordenadas and FOLIUM_AVAILABLE:
                st.subheader("📍 Mapa del lugar del hecho")
                
                coords = denuncia.coordenadas
                st.caption(f"Precisión: {coords.precision} | Fuente: {coords.fuente}")
                
                # Crear mapa centrado en las coordenadas
                mapa = crear_mapa_denuncia(
                    coordenadas=coords,
                    denuncia=denuncia
                )
                
                # Mostrar mapa con key única para evitar problemas de re-render
                st_folium(mapa, width=700, height=400, key="mapa_denuncia")
                
                # Mostrar información de shapefile
                comisaria = denuncia.comisaria_asignada or denuncia.comisaria_detectada
                if comisaria:
                    try:
                        qgis_service = get_qgis_sync_service(repo_root)
                        ruta_shp = qgis_service.obtener_ruta_shapefile_comisaria(comisaria)
                        st.info(f"🗺️ Shapefile destino: {ruta_shp}")
                    except Exception:
                        pass
                        
            elif denuncia.coordenadas and not FOLIUM_AVAILABLE:
                st.warning("Para ver el mapa, instale: `pip install folium streamlit-folium`")
                coords = denuncia.coordenadas
                st.write(f"Coordenadas: {coords.latitud}, {coords.longitud}")
            elif not denuncia.coordenadas and denuncia.direccion_hecho:
                st.info("No se pudieron obtener coordenadas para la dirección detectada")

            if motivo:
                st.warning(f"Enviado a revisión manual: {motivo}")

            if destino:
                st.success(f"Archivo guardado en: {destino}")


if __name__ == "__main__":
    main()
