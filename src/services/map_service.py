from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import folium

from src.models.denuncia import Coordenadas, DenunciaClasificada

logger = logging.getLogger(__name__)

# Colores por tipo de delito
COLORES_DELITO = {
    "HURTO": "blue",
    "ROBO": "red",
    "ESTAFA": "orange",
    "PORTACION_ARMA_FUEGO": "black",
}

# Iconos por tipo de delito
ICONOS_DELITO = {
    "HURTO": "minus-sign",
    "ROBO": "exclamation-sign",
    "ESTAFA": "usd",
    "PORTACION_ARMA_FUEGO": "warning-sign",
}

# Cache para configuración geográfica
_GEO_CONFIG_CACHE: dict[str, Any] | None = None


def _load_geo_config() -> dict[str, Any]:
    """Carga la configuración geográfica de Tucumán."""
    global _GEO_CONFIG_CACHE
    if _GEO_CONFIG_CACHE is not None:
        return _GEO_CONFIG_CACHE
    
    possible_paths = [
        Path(__file__).parent.parent.parent / "config" / "tucuman_geo.json",
        Path("config/tucuman_geo.json"),
    ]
    for p in possible_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                _GEO_CONFIG_CACHE = json.load(f)
            return _GEO_CONFIG_CACHE
    
    # Valores por defecto
    return {
        "centro": {"latitud": -26.8241, "longitud": -65.2226, "zoom_default": 12}
    }


def crear_mapa_base() -> folium.Map:
    """Crea un mapa base centrado en Tucumán."""
    config = _load_geo_config()
    centro = config.get("centro", {})
    
    mapa = folium.Map(
        location=[centro.get("latitud", -26.8241), centro.get("longitud", -65.2226)],
        zoom_start=centro.get("zoom_default", 12),
        tiles="OpenStreetMap"
    )
    
    return mapa


def crear_mapa_denuncia(
    coordenadas: Coordenadas,
    denuncia: DenunciaClasificada | None = None,
    tipo_delito: str | None = None,
    info_adicional: dict | None = None
) -> folium.Map:
    """
    Crea un mapa con un marcador para la denuncia.
    
    Args:
        coordenadas: Coordenadas del lugar del hecho
        denuncia: Objeto DenunciaClasificada (opcional)
        tipo_delito: Tipo de delito para determinar color/icono
        info_adicional: Información adicional para el popup
        
    Returns:
        Mapa de Folium con el marcador
    """
    if not coordenadas or not coordenadas.latitud or not coordenadas.longitud:
        return crear_mapa_base()
    
    # Determinar tipo de delito
    if denuncia and denuncia.tipo_delito:
        tipo = denuncia.tipo_delito
    elif tipo_delito:
        tipo = tipo_delito
    else:
        tipo = "OTRO"
    
    # Crear mapa centrado en la ubicación
    mapa = folium.Map(
        location=[coordenadas.latitud, coordenadas.longitud],
        zoom_start=16,
        tiles="OpenStreetMap"
    )
    
    # Construir contenido del popup
    popup_lines = []
    
    if denuncia:
        if denuncia.tipo_delito:
            popup_lines.append(f"<b>Tipo:</b> {denuncia.tipo_delito}")
        if denuncia.modalidad_delito:
            popup_lines.append(f"<b>Modalidad:</b> {denuncia.modalidad_delito}")
        if denuncia.fecha:
            popup_lines.append(f"<b>Fecha:</b> {denuncia.fecha}")
        if denuncia.comisaria_asignada:
            popup_lines.append(f"<b>Comisaría:</b> {denuncia.comisaria_asignada}")
        if denuncia.direccion_hecho:
            dir_hecho = denuncia.direccion_hecho
            direccion_str = dir_hecho.to_query().replace(", Argentina", "")
            popup_lines.append(f"<b>Dirección:</b> {direccion_str}")
    
    if info_adicional:
        for key, value in info_adicional.items():
            popup_lines.append(f"<b>{key}:</b> {value}")
    
    if coordenadas.precision:
        popup_lines.append(f"<i>Precisión: {coordenadas.precision}</i>")
    
    popup_html = "<br>".join(popup_lines) if popup_lines else "Sin información"
    
    # Agregar marcador
    color = COLORES_DELITO.get(tipo, "gray")
    icon = ICONOS_DELITO.get(tipo, "info-sign")
    
    folium.Marker(
        location=[coordenadas.latitud, coordenadas.longitud],
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{tipo}" if tipo else "Denuncia",
        icon=folium.Icon(color=color, icon=icon)
    ).add_to(mapa)
    
    # Agregar círculo para indicar área aproximada si la precisión no es exacta
    if coordenadas.precision in ("aproximada", "barrio", "localidad"):
        radio = {
            "aproximada": 200,
            "barrio": 500,
            "localidad": 2000
        }.get(coordenadas.precision, 200)
        
        folium.Circle(
            location=[coordenadas.latitud, coordenadas.longitud],
            radius=radio,
            color=color,
            fill=True,
            fill_opacity=0.1,
            popup=f"Área aproximada ({coordenadas.precision})"
        ).add_to(mapa)
    
    return mapa


def agregar_marcador_denuncia(
    mapa: folium.Map,
    coordenadas: Coordenadas,
    denuncia: DenunciaClasificada | None = None,
    tipo_delito: str | None = None
) -> folium.Map:
    """
    Agrega un marcador de denuncia a un mapa existente.
    
    Args:
        mapa: Mapa de Folium existente
        coordenadas: Coordenadas del lugar del hecho
        denuncia: Objeto DenunciaClasificada
        tipo_delito: Tipo de delito
        
    Returns:
        El mismo mapa con el marcador agregado
    """
    if not coordenadas or not coordenadas.latitud or not coordenadas.longitud:
        return mapa
    
    # Determinar tipo de delito
    if denuncia and denuncia.tipo_delito:
        tipo = denuncia.tipo_delito
    elif tipo_delito:
        tipo = tipo_delito
    else:
        tipo = "OTRO"
    
    # Construir popup
    popup_lines = []
    if denuncia:
        if denuncia.tipo_delito:
            popup_lines.append(f"<b>{denuncia.tipo_delito}</b>")
        if denuncia.modalidad_delito:
            popup_lines.append(denuncia.modalidad_delito)
        if denuncia.fecha:
            popup_lines.append(denuncia.fecha)
    
    popup_html = "<br>".join(popup_lines) if popup_lines else tipo
    
    color = COLORES_DELITO.get(tipo, "gray")
    icon = ICONOS_DELITO.get(tipo, "info-sign")
    
    folium.Marker(
        location=[coordenadas.latitud, coordenadas.longitud],
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=tipo,
        icon=folium.Icon(color=color, icon=icon)
    ).add_to(mapa)
    
    return mapa
