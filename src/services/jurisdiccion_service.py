"""
Servicio para validación de jurisdicciones policiales.
Utiliza shapefiles de QGIS para verificar si una ubicación está dentro
de la jurisdicción de una comisaría específica.
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Importación condicional de geopandas (puede no estar instalado)
try:
    import geopandas as gpd
    from shapely.geometry import Point
    GEOPANDAS_DISPONIBLE = True
except ImportError:
    GEOPANDAS_DISPONIBLE = False
    logger.warning("geopandas no está instalado. La validación de jurisdicciones no estará disponible.")


@dataclass
class ResultadoValidacion:
    """Resultado de la validación de jurisdicción."""
    es_valido: bool
    comisaria_esperada: str
    comisaria_real: Optional[str]
    distancia_km: Optional[float]
    mensaje: str
    jurisdicciones_cercanas: List[str]


class JurisdiccionService:
    """
    Servicio para validar si una ubicación corresponde a una jurisdicción policial.
    
    Utiliza los shapefiles de jurisdicciones almacenados en la unidad de red Z:
    para determinar si las coordenadas de un delito están dentro de la jurisdicción
    de la comisaría que recibió la denuncia.
    """
    
    def __init__(self, config_path: str = "config/shapefiles_jurisdicciones.json"):
        """
        Inicializa el servicio de jurisdicciones.
        
        Args:
            config_path: Ruta al archivo de configuración de shapefiles
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._cache_shapefiles: Dict[str, Any] = {}  # Cache de GeoDataFrames
        self._unidad_red_disponible = False
        
        self._cargar_configuracion()
        self._verificar_disponibilidad()
    
    def _cargar_configuracion(self) -> None:
        """Carga la configuración de shapefiles desde el archivo JSON."""
        if not self.config_path.exists():
            logger.warning(f"Archivo de configuración no encontrado: {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            logger.info("Configuración de shapefiles cargada correctamente")
        except Exception as e:
            logger.error(f"Error cargando configuración de shapefiles: {e}")
    
    def _verificar_disponibilidad(self) -> None:
        """Verifica si la unidad de red está disponible."""
        if not self.config:
            return
            
        unidad = self.config.get("unidad_red", "Z:")
        ruta_base = Path(unidad) / self.config.get("ruta_base", "")
        
        self._unidad_red_disponible = ruta_base.exists()
        
        if self._unidad_red_disponible:
            logger.info(f"Unidad de red disponible: {ruta_base}")
        else:
            logger.warning(f"Unidad de red no disponible: {ruta_base}")
    
    def esta_disponible(self) -> bool:
        """
        Verifica si el servicio está disponible (geopandas instalado y red accesible).
        
        Returns:
            True si el servicio puede validar jurisdicciones
        """
        return GEOPANDAS_DISPONIBLE and self._unidad_red_disponible
    
    def refrescar_disponibilidad(self) -> bool:
        """
        Refresca el estado de disponibilidad de la unidad de red.
        
        Returns:
            True si la unidad está disponible
        """
        self._verificar_disponibilidad()
        return self._unidad_red_disponible
    
    def _construir_ruta_shapefile(self, unidad_regional: str, comisaria: str) -> Optional[Path]:
        """
        Construye la ruta completa a un shapefile.
        
        Args:
            unidad_regional: Código de unidad regional (URC, URN, URO, URE, URS)
            comisaria: Código de comisaría
            
        Returns:
            Path al shapefile o None si no existe
        """
        if not self.config:
            return None
            
        unidad = self.config.get("unidad_red", "Z:")
        ruta_base = self.config.get("ruta_base", "")
        
        ur_config = self.config.get("unidades_regionales", {}).get(unidad_regional, {})
        comisarias = ur_config.get("comisarias", {})
        
        ruta_relativa = comisarias.get(comisaria)
        if not ruta_relativa:
            return None
        
        return Path(unidad) / ruta_base / ruta_relativa
    
    def _cargar_shapefile(self, ruta: Path) -> Optional[Any]:
        """
        Carga un shapefile con cache.
        
        Args:
            ruta: Ruta al shapefile
            
        Returns:
            GeoDataFrame o None si falla
        """
        if not GEOPANDAS_DISPONIBLE:
            return None
            
        ruta_str = str(ruta)
        
        # Verificar cache
        if ruta_str in self._cache_shapefiles:
            return self._cache_shapefiles[ruta_str]
        
        if not ruta.exists():
            logger.warning(f"Shapefile no encontrado: {ruta}")
            return None
        
        try:
            gdf = gpd.read_file(ruta)
            self._cache_shapefiles[ruta_str] = gdf
            logger.debug(f"Shapefile cargado: {ruta}")
            return gdf
        except Exception as e:
            logger.error(f"Error cargando shapefile {ruta}: {e}")
            return None
    
    def limpiar_cache(self) -> None:
        """Limpia el cache de shapefiles."""
        self._cache_shapefiles.clear()
        logger.info("Cache de shapefiles limpiado")
    
    def obtener_jurisdiccion_en_punto(
        self,
        latitud: float,
        longitud: float
    ) -> Optional[Tuple[str, str]]:
        """
        Determina qué jurisdicción contiene un punto dado.
        
        Args:
            latitud: Latitud del punto
            longitud: Longitud del punto
            
        Returns:
            Tupla (unidad_regional, comisaria) o None si no se encuentra
        """
        if not self.esta_disponible():
            return None
        
        punto = Point(longitud, latitud)
        
        # Buscar en todas las jurisdicciones
        for ur_code, ur_data in self.config.get("unidades_regionales", {}).items():
            for cria_code in ur_data.get("comisarias", {}).keys():
                ruta = self._construir_ruta_shapefile(ur_code, cria_code)
                if not ruta:
                    continue
                
                gdf = self._cargar_shapefile(ruta)
                if gdf is None:
                    continue
                
                # Verificar si el punto está dentro de algún polígono
                try:
                    for _, row in gdf.iterrows():
                        if row.geometry and row.geometry.contains(punto):
                            return (ur_code, cria_code)
                except Exception as e:
                    logger.error(f"Error verificando geometría: {e}")
                    continue
        
        return None
    
    def validar_jurisdiccion(
        self,
        latitud: float,
        longitud: float,
        comisaria_denuncia: str,
        unidad_regional: Optional[str] = None
    ) -> ResultadoValidacion:
        """
        Valida si una ubicación corresponde a la jurisdicción de una comisaría.
        
        Args:
            latitud: Latitud del hecho
            longitud: Longitud del hecho
            comisaria_denuncia: Nombre de la comisaría donde se realizó la denuncia
            unidad_regional: Código de unidad regional (opcional, se infiere si no se proporciona)
            
        Returns:
            ResultadoValidacion con el resultado de la validación
        """
        if not GEOPANDAS_DISPONIBLE:
            return ResultadoValidacion(
                es_valido=True,  # No podemos validar, asumimos válido
                comisaria_esperada=comisaria_denuncia,
                comisaria_real=None,
                distancia_km=None,
                mensaje="Validación no disponible: geopandas no instalado",
                jurisdicciones_cercanas=[]
            )
        
        if not self._unidad_red_disponible:
            return ResultadoValidacion(
                es_valido=True,  # No podemos validar, asumimos válido
                comisaria_esperada=comisaria_denuncia,
                comisaria_real=None,
                distancia_km=None,
                mensaje="Validación no disponible: unidad de red no accesible",
                jurisdicciones_cercanas=[]
            )
        
        # Normalizar nombre de comisaría para búsqueda
        comisaria_normalizada = self._normalizar_nombre_comisaria(comisaria_denuncia)
        
        # Buscar jurisdicción que contiene el punto
        resultado = self.obtener_jurisdiccion_en_punto(latitud, longitud)
        
        if resultado is None:
            return ResultadoValidacion(
                es_valido=False,
                comisaria_esperada=comisaria_denuncia,
                comisaria_real=None,
                distancia_km=None,
                mensaje="El punto no está dentro de ninguna jurisdicción conocida",
                jurisdicciones_cercanas=self._buscar_jurisdicciones_cercanas(latitud, longitud)
            )
        
        ur_real, cria_real = resultado
        
        # Verificar si coincide con la comisaría de la denuncia
        cria_real_normalizada = self._normalizar_nombre_comisaria(cria_real)
        
        if cria_real_normalizada == comisaria_normalizada:
            return ResultadoValidacion(
                es_valido=True,
                comisaria_esperada=comisaria_denuncia,
                comisaria_real=cria_real,
                distancia_km=0,
                mensaje="La ubicación corresponde a la jurisdicción correcta",
                jurisdicciones_cercanas=[]
            )
        else:
            return ResultadoValidacion(
                es_valido=False,
                comisaria_esperada=comisaria_denuncia,
                comisaria_real=cria_real,
                distancia_km=None,
                mensaje=f"La ubicación corresponde a {cria_real} ({ur_real}), no a {comisaria_denuncia}",
                jurisdicciones_cercanas=[cria_real]
            )
    
    def _normalizar_nombre_comisaria(self, nombre: str) -> str:
        """
        Normaliza el nombre de una comisaría para comparación.
        
        Args:
            nombre: Nombre de la comisaría
            
        Returns:
            Nombre normalizado
        """
        import unicodedata
        
        # Convertir a mayúsculas
        nombre = nombre.upper()
        
        # Remover acentos
        nombre = unicodedata.normalize('NFD', nombre)
        nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
        
        # Remover prefijos comunes
        prefijos = ['COMISARIA ', 'CRIA ', 'CRIA. ', 'SUBCOMISARIA ', 'DESTACAMENTO ']
        for prefijo in prefijos:
            if nombre.startswith(prefijo):
                nombre = nombre[len(prefijo):]
        
        # Remover sufijos de unidad regional
        sufijos = ['-URC', '-URN', '-URO', '-URE', '-URS', ' URC', ' URN', ' URO', ' URE', ' URS']
        for sufijo in sufijos:
            if nombre.endswith(sufijo):
                nombre = nombre[:-len(sufijo)]
        
        # Limpiar espacios
        nombre = ' '.join(nombre.split())
        
        return nombre
    
    def _buscar_jurisdicciones_cercanas(
        self,
        latitud: float,
        longitud: float,
        limite: int = 5
    ) -> List[str]:
        """
        Busca las jurisdicciones más cercanas a un punto.
        
        Args:
            latitud: Latitud del punto
            longitud: Longitud del punto
            limite: Número máximo de resultados
            
        Returns:
            Lista de nombres de jurisdicciones cercanas
        """
        # Implementación simplificada - retorna lista vacía
        # TODO: Implementar búsqueda por distancia
        return []
    
    def obtener_todas_comisarias(self) -> Dict[str, List[str]]:
        """
        Obtiene todas las comisarías configuradas por unidad regional.
        
        Returns:
            Diccionario con unidades regionales como claves y listas de comisarías
        """
        resultado = {}
        
        for ur_code, ur_data in self.config.get("unidades_regionales", {}).items():
            resultado[ur_code] = {
                "nombre": ur_data.get("nombre", ur_code),
                "comisarias": list(ur_data.get("comisarias", {}).keys())
            }
        
        return resultado
    
    def obtener_info_estado(self) -> Dict[str, Any]:
        """
        Obtiene información del estado del servicio.
        
        Returns:
            Diccionario con información del estado
        """
        total_comisarias = 0
        for ur_data in self.config.get("unidades_regionales", {}).values():
            total_comisarias += len(ur_data.get("comisarias", {}))
        
        return {
            "geopandas_disponible": GEOPANDAS_DISPONIBLE,
            "unidad_red_disponible": self._unidad_red_disponible,
            "servicio_operativo": self.esta_disponible(),
            "unidad_red": self.config.get("unidad_red", "Z:"),
            "ruta_base": self.config.get("ruta_base", ""),
            "total_comisarias_configuradas": total_comisarias,
            "shapefiles_en_cache": len(self._cache_shapefiles)
        }
