from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.config_loader import load_config
from src.procesador import procesar_archivo
from src.utils.logging_setup import setup_logging

# Importaciones para el mapa
try:
    from streamlit_folium import st_folium
    from src.services.map_service import crear_mapa_denuncia, agregar_marcador_denuncia
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")

    cfg = load_config(repo_root)
    setup_logging(repo_root, cfg)

    st.set_page_config(page_title="SCID", layout="centered")
    st.title("Sistema de Clasificación Inteligente de Denuncias (SCID)")

    st.caption("Carga una denuncia (PDF/Imagen). El sistema extrae texto, clasifica y archiva.")

    uploaded = st.file_uploader("Denuncia", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=False)

    if uploaded is None:
        st.info("Esperando archivo…")
        return

    st.write(f"Archivo: {uploaded.name} ({uploaded.type})")

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

        st.subheader("Texto extraído")
        st.text_area("", value=texto[:20000], height=240)

        st.subheader("Resultado")
        if denuncia is None:
            st.error(f"No se pudo clasificar. Motivo: {motivo or 'Desconocido'}")
            return

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
            mapa = crear_mapa_denuncia(coords.latitud, coords.longitud, zoom=16)
            agregar_marcador_denuncia(
                mapa=mapa,
                latitud=coords.latitud,
                longitud=coords.longitud,
                tipo_delito=denuncia.tipo_delito,
                modalidad=denuncia.modalidad_delito,
                fecha=denuncia.fecha,
                direccion=denuncia.direccion_hecho.to_query() if denuncia.direccion_hecho else None,
                precision=coords.precision,
            )
            
            # Mostrar mapa
            st_folium(mapa, width=700, height=400)
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
