from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.config_loader import load_config
from src.procesador import procesar_archivo
from src.utils.logging_setup import setup_logging


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

        st.write(
            {
                "fecha": denuncia.fecha,
                "comisaria_detectada": denuncia.comisaria_detectada,
                "tipo_delito": denuncia.tipo_delito,
                "region_asignada": denuncia.region_asignada,
                "comisaria_asignada": denuncia.comisaria_asignada,
                "score_match": denuncia.score_match,
            }
        )

        if motivo:
            st.warning(f"Enviado a revisión manual: {motivo}")

        if destino:
            st.success(f"Archivo guardado en: {destino}")


if __name__ == "__main__":
    main()
