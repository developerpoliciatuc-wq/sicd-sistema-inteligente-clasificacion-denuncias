from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from src.models.denuncia import DireccionHecho, Coordenadas

logger = logging.getLogger(__name__)

# Cache para configuración geográfica
_GEO_CONFIG_CACHE: dict[str, Any] | None = None


def _load_geo_config(config_path: Path | None = None) -> dict[str, Any]:
    """Carga la configuración geográfica de Tucumán."""
    global _GEO_CONFIG_CACHE
    if _GEO_CONFIG_CACHE is not None:
        return _GEO_CONFIG_CACHE
    
    if config_path is None:
        possible_paths = [
            Path(__file__).parent.parent.parent / "config" / "tucuman_geo.json",
            Path("config/tucuman_geo.json"),
        ]
        for p in possible_paths:
            if p.exists():
                config_path = p
                break
    
    if config_path is None or not config_path.exists():
        logger.warning("No se encontró archivo de configuración geográfica")
        return {
            "bounds": {"norte": -26.0, "sur": -28.0, "este": -64.5, "oeste": -66.5},
            "centro": {"latitud": -26.8241, "longitud": -65.2226}
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        _GEO_CONFIG_CACHE = json.load(f)
    return _GEO_CONFIG_CACHE


class GeocodingService:
    """Servicio de geocodificación usando Nominatim (OpenStreetMap)."""
    
    def __init__(self):
        self.geocoder = Nominatim(user_agent="sicd-tucuman-policia-v1")
        self.config = _load_geo_config()
        self.bounds = self.config.get("bounds", {})
        self._last_request_time = 0
        self._min_delay = 1.0  # Nominatim requiere 1 segundo entre requests
    
    def _rate_limit(self) -> None:
        """Aplica rate limiting para respetar los límites de Nominatim."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_delay:
            time.sleep(self._min_delay - elapsed)
        self._last_request_time = time.time()
    
    def _validar_tucuman(self, lat: float, lng: float) -> bool:
        """Verifica que las coordenadas estén dentro de los límites de Tucumán."""
        return (
            self.bounds.get("sur", -28.0) <= lat <= self.bounds.get("norte", -26.0) and
            self.bounds.get("oeste", -66.5) <= lng <= self.bounds.get("este", -64.5)
        )
    
    def geocodificar(self, direccion: DireccionHecho) -> Coordenadas | None:
        """
        Convierte una dirección a coordenadas geográficas.
        
        Args:
            direccion: Objeto DireccionHecho con los datos de ubicación
            
        Returns:
            Coordenadas si se encontró la ubicación, None en caso contrario
        """
        if not direccion:
            return None
        
        query = direccion.to_query()
        if not query or query == "Tucumán, Argentina":
            logger.debug("Query de geocodificación vacía o genérica")
            return None
        
        self._rate_limit()
        
        try:
            logger.info(f"Geocodificando: {query}")
            
            # Intentar con viewbox de Tucumán para mejorar precisión
            location = self.geocoder.geocode(
                query,
                country_codes="ar",
                viewbox=[
                    (self.bounds.get("norte", -26.0), self.bounds.get("oeste", -66.5)),
                    (self.bounds.get("sur", -28.0), self.bounds.get("este", -64.5))
                ],
                bounded=True,
                timeout=10
            )
            
            if location:
                lat, lng = location.latitude, location.longitude
                
                if self._validar_tucuman(lat, lng):
                    logger.info(f"Geocodificación exitosa: ({lat}, {lng})")
                    return Coordenadas(
                        latitud=lat,
                        longitud=lng,
                        precision="aproximada",
                        fuente="nominatim"
                    )
                else:
                    logger.warning(f"Coordenadas fuera de Tucumán: ({lat}, {lng})")
            else:
                logger.warning(f"No se encontraron resultados para: {query}")
                
        except GeocoderTimedOut:
            logger.error(f"Timeout al geocodificar: {query}")
        except GeocoderServiceError as e:
            logger.error(f"Error del servicio de geocodificación: {e}")
        except Exception as e:
            logger.exception(f"Error inesperado al geocodificar: {e}")
        
        return None
    
    def geocodificar_con_fallback(self, direccion: DireccionHecho) -> Coordenadas | None:
        """
        Intenta geocodificar con múltiples estrategias de fallback.
        
        1. Query completa
        2. Solo calle principal + localidad
        3. Solo localidad
        """
        # Intento 1: Query completa
        coords = self.geocodificar(direccion)
        if coords:
            return coords
        
        # Intento 2: Simplificar a calle + localidad
        if direccion.calle_principal:
            direccion_simple = DireccionHecho(
                calle_principal=direccion.calle_principal,
                localidad=direccion.localidad or "San Miguel de Tucumán"
            )
            coords = self.geocodificar(direccion_simple)
            if coords:
                return Coordenadas(
                    latitud=coords.latitud,
                    longitud=coords.longitud,
                    precision="aproximada",
                    fuente=coords.fuente
                )
        
        # Intento 3: Solo localidad (baja precisión)
        if direccion.localidad:
            direccion_localidad = DireccionHecho(localidad=direccion.localidad)
            coords = self.geocodificar(direccion_localidad)
            if coords:
                return Coordenadas(
                    latitud=coords.latitud,
                    longitud=coords.longitud,
                    precision="localidad",
                    fuente=coords.fuente
                )
        
        return None


# Instancia global del servicio (singleton)
_geocoding_service: GeocodingService | None = None


def get_geocoding_service() -> GeocodingService:
    """Obtiene la instancia del servicio de geocodificación."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
