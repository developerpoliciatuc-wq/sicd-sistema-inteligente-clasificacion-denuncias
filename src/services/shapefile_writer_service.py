"""
Servicio para escribir puntos de delitos directamente en los shapefiles de la red.
Escribe en las carpetas Z: de QGIS correspondientes a cada comisaría.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import logging

try:
    import geopandas as gpd
    from shapely.geometry import Point
    import fiona
    GEOPANDAS_DISPONIBLE = True
except ImportError:
    GEOPANDAS_DISPONIBLE = False

logger = logging.getLogger(__name__)


class ShapefileWriterService:
    """
    Servicio para escribir puntos de delitos directamente en shapefiles existentes.
    
    Lee la configuración de config/shapefiles_jurisdicciones.json para determinar
    la ruta del shapefile según la comisaría de la denuncia.
    """
    
    def __init__(self, config_path: str = None):
        """
        Inicializa el servicio.
        
        Args:
            config_path: Ruta al archivo de configuración JSON. Si no se proporciona,
                        usa config/shapefiles_jurisdicciones.json
        """
        if not GEOPANDAS_DISPONIBLE:
            logger.error("geopandas no está instalado. Ejecute: pip install geopandas")
            raise ImportError("geopandas es requerido para ShapefileWriterService")
        
        if config_path is None:
            # Buscar config relativo al proyecto
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "shapefiles_jurisdicciones.json"
        
        self.config_path = Path(config_path)
        self._config = self._cargar_configuracion()
        self._mapeo_comisarias = self._construir_mapeo_comisarias()
        
    def _cargar_configuracion(self) -> Dict:
        """Carga la configuración de shapefiles desde el JSON."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    def _construir_mapeo_comisarias(self) -> Dict[str, str]:
        """
        Construye un mapeo de nombre de comisaría a ruta completa del shapefile.
        Incluye alias comunes y abreviaturas.
        
        Returns:
            Diccionario {nombre_comisaria: ruta_shapefile}
        """
        mapeo = {}
        unidad_red = self._config.get("unidad_red", "Z:")
        ruta_base = self._config.get("ruta_base", "")
        
        # Alias comunes para comisarías (nombre_config -> nombres_alternativos)
        alias_comunes = {
            "VILLA_BENJAMIN_ARAOZ": ["VILLA B. ARAOZ", "VILLA B ARAOZ", "VILLA BENJAMIN ARAOZ", "V. B. ARAOZ"],
            "GOB_PIEDRABUENA": ["PIEDRABUENA", "GOB PIEDRABUENA", "GOBERNADOR PIEDRABUENA"],
            "VILLA_PADRE_MONTI": ["VILLA P. MONTI", "VILLA P MONTI", "V. P. MONTI", "V.P.MONTI"],
            "7_DE_ABRIL": ["7 DE ABRIL", "SIETE DE ABRIL"],
            "SANTA_CRUZ_LA_TUNA": ["SANTA CRUZ Y LA TUNA", "SANTA CRUZ", "LA TUNA"],
            "LOS_SOSA_SOLDADO_MALDONADO": ["LOS SOSA", "SOLDADO MALDONADO", "LOS SOSA Y SOLDADO MALDONADO"],
            "LOS_GOMES": ["LOS GOMEZ", "LOS GOMES"],
            "CAMPO_QUIMIL": ["CAMPO EL QUIMIL", "CAMPO QUIMIL", "EL QUIMIL"],
            "EL_CHANAR": ["EL CHAÑAR", "EL CHANAR"],
        }
        
        for ur_key, ur_data in self._config.get("unidades_regionales", {}).items():
            for cria_key, ruta_relativa in ur_data.get("comisarias", {}).items():
                ruta_completa = f"{unidad_red}/{ruta_base}/{ruta_relativa}"
                
                # Agregar nombre normalizado
                nombre_normalizado = self._normalizar_nombre_comisaria(cria_key)
                mapeo[nombre_normalizado] = ruta_completa
                
                # Agregar variantes comunes
                mapeo[cria_key.upper()] = ruta_completa
                mapeo[cria_key.lower()] = ruta_completa
                mapeo[cria_key.replace("_", " ").upper()] = ruta_completa
                mapeo[cria_key.replace("_", " ").lower()] = ruta_completa
                
                # Agregar alias si existen
                if cria_key in alias_comunes:
                    for alias in alias_comunes[cria_key]:
                        mapeo[alias.upper()] = ruta_completa
                        mapeo[self._normalizar_nombre_comisaria(alias)] = ruta_completa
                
                # Agregar sin prefijo "CRIA " si aplica
                nombre_sin_cria = cria_key.replace("CRIA_", "").replace("CRIA", "")
                if nombre_sin_cria:
                    mapeo[nombre_sin_cria.upper()] = ruta_completa
                    mapeo[nombre_sin_cria.replace("_", " ").upper()] = ruta_completa
        
        # Agregar capas especiales
        for capa_key, ruta_relativa in self._config.get("capas_especiales", {}).items():
            ruta_completa = f"{unidad_red}/{ruta_base}/{ruta_relativa}"
            mapeo[capa_key.upper()] = ruta_completa
            mapeo[capa_key.lower()] = ruta_completa
        
        logger.info(f"Mapeo de comisarías construido: {len(mapeo)} entradas")
        return mapeo
    
    def _normalizar_nombre_comisaria(self, nombre: str) -> str:
        """
        Normaliza el nombre de una comisaría para facilitar el matching.
        
        Args:
            nombre: Nombre de la comisaría
            
        Returns:
            Nombre normalizado
        """
        import unicodedata
        # Normalizar acentos
        nombre = unicodedata.normalize('NFKD', nombre).encode('ASCII', 'ignore').decode('ASCII')
        # Convertir a mayúsculas
        nombre = nombre.upper()
        # Reemplazar guiones y espacios por underscores
        nombre = nombre.replace("-", "_").replace(" ", "_")
        # Eliminar caracteres especiales
        nombre = ''.join(c for c in nombre if c.isalnum() or c == '_')
        return nombre
    
    def _buscar_shapefile_para_comisaria(self, comisaria: str) -> Optional[str]:
        """
        Busca el shapefile correspondiente a una comisaría.
        
        Args:
            comisaria: Nombre de la comisaría (puede ser en varios formatos)
            
        Returns:
            Ruta al shapefile o None si no se encuentra
        """
        # Probar nombre directo
        if comisaria in self._mapeo_comisarias:
            return self._mapeo_comisarias[comisaria]
        
        # Probar normalizado
        nombre_normalizado = self._normalizar_nombre_comisaria(comisaria)
        if nombre_normalizado in self._mapeo_comisarias:
            return self._mapeo_comisarias[nombre_normalizado]
        
        # Buscar por coincidencia parcial
        for key, ruta in self._mapeo_comisarias.items():
            if nombre_normalizado in key or key in nombre_normalizado:
                return ruta
        
        # Buscar "CRIA" + nombre
        cria_nombre = f"CRIA_{nombre_normalizado}"
        if cria_nombre in self._mapeo_comisarias:
            return self._mapeo_comisarias[cria_nombre]
        
        # Buscar sin prefijo CRIA
        for key, ruta in self._mapeo_comisarias.items():
            key_sin_cria = key.replace("CRIA_", "").replace("CRIA", "")
            if nombre_normalizado == key_sin_cria:
                return ruta
        
        logger.warning(f"No se encontró shapefile para comisaría: {comisaria}")
        return None
    
    def agregar_punto_a_shapefile(
        self,
        comisaria: str,
        latitud: float,
        longitud: float,
        tipo_delito: str,
        modalidad: str,
        numero_denuncia: str,
        fecha_hecho: str,
        direccion: str = "",
        datos_adicionales: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Agrega un punto de delito al shapefile correspondiente a la comisaría.
        
        Args:
            comisaria: Nombre de la comisaría
            latitud: Latitud del punto
            longitud: Longitud del punto
            tipo_delito: Tipo de delito
            modalidad: Modalidad del delito
            numero_denuncia: Número de denuncia
            fecha_hecho: Fecha del hecho
            direccion: Dirección del hecho
            datos_adicionales: Diccionario con datos extra
            
        Returns:
            Tupla (éxito: bool, mensaje: str)
        """
        # Buscar shapefile correspondiente
        ruta_shapefile = self._buscar_shapefile_para_comisaria(comisaria)
        
        if not ruta_shapefile:
            return False, f"No se encontró shapefile para comisaría: {comisaria}"
        
        # Convertir ruta a Path y verificar existencia
        ruta_path = Path(ruta_shapefile.replace("/", os.sep))
        
        if not ruta_path.exists():
            logger.warning(f"Shapefile no existe: {ruta_path}")
            # Intentar crear el shapefile si la carpeta existe
            if ruta_path.parent.exists():
                return self._crear_nuevo_shapefile_con_punto(
                    ruta_path, latitud, longitud, tipo_delito, modalidad,
                    numero_denuncia, fecha_hecho, direccion, datos_adicionales
                )
            return False, f"Shapefile no existe y no se puede crear: {ruta_path}"
        
        try:
            # Leer shapefile existente
            gdf = gpd.read_file(ruta_path)
            
            # Crear nuevo punto
            punto = Point(longitud, latitud)
            
            # Crear diccionario de atributos adaptándose al schema existente
            atributos = self._adaptar_atributos_a_schema(
                gdf, tipo_delito, modalidad, numero_denuncia, 
                fecha_hecho, direccion, datos_adicionales
            )
            
            # Crear nueva fila
            nueva_fila = gpd.GeoDataFrame(
                [atributos],
                geometry=[punto],
                crs=gdf.crs
            )
            
            # Agregar al GeoDataFrame existente
            gdf = gpd.GeoDataFrame(
                pd.concat([gdf, nueva_fila], ignore_index=True),
                crs=gdf.crs
            )
            
            # Guardar
            gdf.to_file(ruta_path, driver="ESRI Shapefile", encoding='utf-8')
            
            logger.info(f"Punto agregado exitosamente a {ruta_path}")
            return True, f"Punto agregado a {ruta_path}"
            
        except Exception as e:
            logger.error(f"Error agregando punto a shapefile: {e}")
            return False, f"Error: {str(e)}"
    
    def _adaptar_atributos_a_schema(
        self,
        gdf: 'gpd.GeoDataFrame',
        tipo_delito: str,
        modalidad: str,
        numero_denuncia: str,
        fecha_hecho: str,
        direccion: str,
        datos_adicionales: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Adapta los atributos al schema del shapefile existente.
        
        Args:
            gdf: GeoDataFrame existente
            tipo_delito: Tipo de delito
            modalidad: Modalidad
            numero_denuncia: Número de denuncia
            fecha_hecho: Fecha del hecho
            direccion: Dirección
            datos_adicionales: Datos extra
            
        Returns:
            Diccionario con atributos adaptados
        """
        atributos = {}
        columnas = list(gdf.columns)
        columnas_lower = [c.lower() for c in columnas]
        
        # Mapeo de campos comunes
        mapeo_campos = {
            'tipo_delito': ['tipo_delit', 'tipo', 'delito', 'tipodelit', 'tip_delito'],
            'modalidad': ['modalidad', 'mod', 'modal', 'modalid'],
            'numero_denuncia': ['nro_denunc', 'denuncia', 'nro_den', 'num_den', 'id'],
            'fecha_hecho': ['fecha', 'fecha_hech', 'fecha_h', 'fec_hecho', 'date'],
            'direccion': ['direccion', 'dir', 'domicilio', 'ubicacion', 'calle'],
        }
        
        valores = {
            'tipo_delito': tipo_delito,
            'modalidad': modalidad,
            'numero_denuncia': numero_denuncia,
            'fecha_hecho': fecha_hecho,
            'direccion': direccion
        }
        
        # Asignar valores a campos existentes
        for valor_key, posibles_nombres in mapeo_campos.items():
            valor = valores.get(valor_key, '')
            for nombre in posibles_nombres:
                for i, col_lower in enumerate(columnas_lower):
                    if nombre in col_lower or col_lower in nombre:
                        col_original = columnas[i]
                        if col_original != 'geometry':
                            # Truncar si es necesario para shapefiles (limite 254 chars)
                            if isinstance(valor, str) and len(valor) > 254:
                                valor = valor[:254]
                            atributos[col_original] = valor
                            break
        
        # Agregar datos adicionales si coinciden con columnas
        if datos_adicionales:
            for key, valor in datos_adicionales.items():
                key_lower = key.lower()
                for i, col_lower in enumerate(columnas_lower):
                    if key_lower == col_lower:
                        col_original = columnas[i]
                        if col_original != 'geometry':
                            atributos[col_original] = valor
                            break
        
        # Rellenar columnas faltantes con valores por defecto
        for col in columnas:
            if col != 'geometry' and col not in atributos:
                atributos[col] = None
        
        return atributos
    
    def _crear_nuevo_shapefile_con_punto(
        self,
        ruta_path: Path,
        latitud: float,
        longitud: float,
        tipo_delito: str,
        modalidad: str,
        numero_denuncia: str,
        fecha_hecho: str,
        direccion: str,
        datos_adicionales: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Crea un nuevo shapefile con el primer punto.
        
        Returns:
            Tupla (éxito: bool, mensaje: str)
        """
        try:
            import pandas as pd
            
            # Crear punto
            punto = Point(longitud, latitud)
            
            # Schema básico para nuevo shapefile
            data = {
                'nro_denunc': [numero_denuncia],
                'tipo_delit': [tipo_delito[:50] if tipo_delito else ''],
                'modalidad': [modalidad[:50] if modalidad else ''],
                'fecha': [fecha_hecho[:20] if fecha_hecho else ''],
                'direccion': [direccion[:100] if direccion else ''],
                'geometry': [punto]
            }
            
            # Crear GeoDataFrame
            gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")
            
            # Guardar
            gdf.to_file(ruta_path, driver="ESRI Shapefile", encoding='utf-8')
            
            logger.info(f"Nuevo shapefile creado: {ruta_path}")
            return True, f"Nuevo shapefile creado: {ruta_path}"
            
        except Exception as e:
            logger.error(f"Error creando shapefile: {e}")
            return False, f"Error creando shapefile: {str(e)}"
    
    def verificar_conexion_red(self) -> Tuple[bool, str]:
        """
        Verifica si la unidad de red está accesible.
        
        Returns:
            Tupla (conectado: bool, mensaje: str)
        """
        unidad_red = self._config.get("unidad_red", "Z:")
        ruta_base = self._config.get("ruta_base", "")
        
        ruta_test = Path(f"{unidad_red}/{ruta_base}")
        
        if ruta_test.exists():
            return True, f"Conexión exitosa a {ruta_test}"
        else:
            return False, f"No se puede acceder a {ruta_test}"
    
    def listar_shapefiles_disponibles(self) -> Dict[str, str]:
        """
        Lista todos los shapefiles configurados y su estado.
        
        Returns:
            Diccionario {comisaria: estado}
        """
        resultado = {}
        for nombre, ruta in self._mapeo_comisarias.items():
            ruta_path = Path(ruta.replace("/", os.sep))
            if ruta_path.exists():
                resultado[nombre] = f"✓ {ruta}"
            else:
                resultado[nombre] = f"✗ {ruta} (no existe)"
        return resultado
    
    def obtener_ruta_shapefile(self, comisaria: str) -> Optional[str]:
        """
        Obtiene la ruta del shapefile para una comisaría.
        
        Args:
            comisaria: Nombre de la comisaría
            
        Returns:
            Ruta al shapefile o None
        """
        return self._buscar_shapefile_para_comisaria(comisaria)


# Importar pandas aquí para evitar error circular
try:
    import pandas as pd
except ImportError:
    pass
