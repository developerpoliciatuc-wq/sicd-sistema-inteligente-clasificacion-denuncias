"""
Servicio de sincronización en tiempo real con QGIS.
Genera archivos GeoJSON que QGIS puede monitorear para actualización automática.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PuntoDelito:
    """Representa un punto de delito georreferenciado."""
    id: str
    latitud: float
    longitud: float
    tipo_delito: str
    modalidad: str
    comisaria: str
    fecha_hecho: str
    fecha_registro: datetime
    direccion: str
    numero_denuncia: str
    
    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convierte el punto a un Feature GeoJSON."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitud, self.latitud]  # GeoJSON usa [lng, lat]
            },
            "properties": {
                "id": self.id,
                "tipo_delito": self.tipo_delito,
                "modalidad": self.modalidad,
                "comisaria": self.comisaria,
                "fecha_hecho": self.fecha_hecho,
                "fecha_registro": self.fecha_registro.isoformat(),
                "direccion": self.direccion,
                "numero_denuncia": self.numero_denuncia,
                "color": self._get_color()
            }
        }
    
    def _get_color(self) -> str:
        """Retorna el color según el tipo de delito."""
        colores = {
            "HURTO": "#0000FF",       # Azul
            "ROBO": "#FF0000",         # Rojo
            "ESTAFA": "#FFA500",       # Naranja
            "PORTACION_ARMA_FUEGO": "#000000"  # Negro
        }
        return colores.get(self.tipo_delito, "#808080")  # Gris por defecto


class QGISSyncService:
    """
    Servicio para sincronización en tiempo real con QGIS.
    
    Genera archivos GeoJSON que QGIS puede monitorear y actualizar automáticamente.
    Soporta:
    - Actualización en tiempo real de puntos
    - Archivo histórico manual
    - Estadísticas de delitos
    """
    
    ARCHIVO_ACTIVO = "denuncias_activas.geojson"
    CARPETA_HISTORICO = "historico"
    
    def __init__(self, ruta_sync: str):
        """
        Inicializa el servicio de sincronización.
        
        Args:
            ruta_sync: Ruta a la carpeta de sincronización QGIS (ej: data/OUTPUT/QGIS_SYNC)
        """
        self.ruta_sync = Path(ruta_sync)
        self.ruta_archivo_activo = self.ruta_sync / self.ARCHIVO_ACTIVO
        self.ruta_historico = self.ruta_sync / self.CARPETA_HISTORICO
        
        # Inicializar puntos vacío ANTES de inicializar estructura
        self._puntos: Dict[str, PuntoDelito] = {}
        
        # Crear estructura de carpetas si no existe
        self._inicializar_estructura()
        
        # Cargar puntos existentes
        self._cargar_puntos_existentes()
    
    def _inicializar_estructura(self) -> None:
        """Crea la estructura de carpetas necesaria."""
        self.ruta_sync.mkdir(parents=True, exist_ok=True)
        self.ruta_historico.mkdir(parents=True, exist_ok=True)
        
        # Crear archivo GeoJSON vacío si no existe
        if not self.ruta_archivo_activo.exists():
            self._guardar_geojson()
    
    def _cargar_puntos_existentes(self) -> None:
        """Carga puntos desde el archivo GeoJSON activo."""
        if not self.ruta_archivo_activo.exists():
            return
            
        try:
            with open(self.ruta_archivo_activo, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                
                punto = PuntoDelito(
                    id=props.get('id', ''),
                    latitud=coords[1],  # GeoJSON: [lng, lat]
                    longitud=coords[0],
                    tipo_delito=props.get('tipo_delito', ''),
                    modalidad=props.get('modalidad', ''),
                    comisaria=props.get('comisaria', ''),
                    fecha_hecho=props.get('fecha_hecho', ''),
                    fecha_registro=datetime.fromisoformat(props.get('fecha_registro', datetime.now().isoformat())),
                    direccion=props.get('direccion', ''),
                    numero_denuncia=props.get('numero_denuncia', '')
                )
                self._puntos[punto.id] = punto
                
            logger.info(f"Cargados {len(self._puntos)} puntos existentes del archivo GeoJSON")
        except Exception as e:
            logger.error(f"Error cargando puntos existentes: {e}")
    
    def _guardar_geojson(self) -> None:
        """Guarda los puntos actuales en el archivo GeoJSON."""
        geojson = {
            "type": "FeatureCollection",
            "name": "denuncias_activas",
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                }
            },
            "features": [p.to_geojson_feature() for p in self._puntos.values()]
        }
        
        # Escribir archivo de forma atómica (primero temporal, luego renombrar)
        ruta_temp = self.ruta_archivo_activo.with_suffix('.tmp')
        try:
            with open(ruta_temp, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)
            
            # Renombrar atómicamente
            ruta_temp.replace(self.ruta_archivo_activo)
            logger.debug(f"Archivo GeoJSON guardado: {len(self._puntos)} puntos")
        except Exception as e:
            logger.error(f"Error guardando archivo GeoJSON: {e}")
            if ruta_temp.exists():
                ruta_temp.unlink()
            raise
    
    def agregar_denuncia(
        self,
        numero_denuncia: str,
        latitud: float,
        longitud: float,
        tipo_delito: str,
        modalidad: str,
        comisaria: str,
        fecha_hecho: str,
        direccion: str = ""
    ) -> PuntoDelito:
        """
        Agrega una nueva denuncia al mapa.
        
        Args:
            numero_denuncia: Número de denuncia (ej: "D-563745-2025")
            latitud: Latitud del hecho
            longitud: Longitud del hecho
            tipo_delito: Tipo de delito (ROBO, HURTO, ESTAFA, PORTACION_ARMA_FUEGO)
            modalidad: Modalidad del delito
            comisaria: Comisaría que recibió la denuncia
            fecha_hecho: Fecha del hecho
            direccion: Dirección del hecho
            
        Returns:
            PuntoDelito creado
        """
        punto = PuntoDelito(
            id=numero_denuncia,
            latitud=latitud,
            longitud=longitud,
            tipo_delito=tipo_delito,
            modalidad=modalidad,
            comisaria=comisaria,
            fecha_hecho=fecha_hecho,
            fecha_registro=datetime.now(),
            direccion=direccion,
            numero_denuncia=numero_denuncia
        )
        
        self._puntos[punto.id] = punto
        self._guardar_geojson()
        
        logger.info(f"Denuncia agregada al mapa: {numero_denuncia} ({tipo_delito} - {modalidad})")
        return punto
    
    def eliminar_denuncia(self, numero_denuncia: str) -> bool:
        """
        Elimina una denuncia del mapa activo.
        
        Args:
            numero_denuncia: Número de denuncia a eliminar
            
        Returns:
            True si se eliminó, False si no existía
        """
        if numero_denuncia in self._puntos:
            del self._puntos[numero_denuncia]
            self._guardar_geojson()
            logger.info(f"Denuncia eliminada del mapa: {numero_denuncia}")
            return True
        return False
    
    def limpiar_archivo(self) -> int:
        """
        Limpia todas las denuncias del archivo activo.
        
        Returns:
            Número de denuncias eliminadas
        """
        cantidad = len(self._puntos)
        self._puntos.clear()
        self._guardar_geojson()
        logger.info(f"Archivo de denuncias activas limpiado: {cantidad} puntos eliminados")
        return cantidad
    
    def archivar_historico(self, nombre_archivo: Optional[str] = None) -> str:
        """
        Archiva las denuncias actuales en el histórico.
        
        Args:
            nombre_archivo: Nombre personalizado para el archivo (opcional)
            
        Returns:
            Ruta del archivo histórico creado
        """
        if not self._puntos:
            logger.warning("No hay denuncias para archivar")
            return ""
        
        # Generar nombre de archivo con timestamp
        if not nombre_archivo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"denuncias_{timestamp}.geojson"
        
        ruta_destino = self.ruta_historico / nombre_archivo
        
        # Copiar archivo activo al histórico
        shutil.copy2(self.ruta_archivo_activo, ruta_destino)
        
        # Limpiar archivo activo
        cantidad = self.limpiar_archivo()
        
        logger.info(f"Archivo histórico creado: {ruta_destino} ({cantidad} denuncias)")
        return str(ruta_destino)
    
    def obtener_estadisticas(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de las denuncias activas.
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "total_denuncias": len(self._puntos),
            "por_tipo_delito": {},
            "por_comisaria": {},
            "por_modalidad": {},
            "ultima_actualizacion": datetime.now().isoformat()
        }
        
        for punto in self._puntos.values():
            # Por tipo de delito
            stats["por_tipo_delito"][punto.tipo_delito] = \
                stats["por_tipo_delito"].get(punto.tipo_delito, 0) + 1
            
            # Por comisaría
            stats["por_comisaria"][punto.comisaria] = \
                stats["por_comisaria"].get(punto.comisaria, 0) + 1
            
            # Por modalidad
            stats["por_modalidad"][punto.modalidad] = \
                stats["por_modalidad"].get(punto.modalidad, 0) + 1
        
        return stats
    
    def obtener_puntos(self) -> List[PuntoDelito]:
        """Retorna lista de todos los puntos activos."""
        return list(self._puntos.values())
    
    def obtener_ruta_archivo_activo(self) -> str:
        """Retorna la ruta absoluta del archivo GeoJSON activo."""
        return str(self.ruta_archivo_activo.absolute())
    
    def listar_archivos_historicos(self) -> List[Dict[str, Any]]:
        """
        Lista los archivos históricos disponibles.
        
        Returns:
            Lista de diccionarios con información de cada archivo
        """
        archivos = []
        for archivo in self.ruta_historico.glob("*.geojson"):
            stat = archivo.stat()
            archivos.append({
                "nombre": archivo.name,
                "ruta": str(archivo),
                "fecha_creacion": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "tamaño_bytes": stat.st_size
            })
        
        # Ordenar por fecha de creación (más reciente primero)
        archivos.sort(key=lambda x: x["fecha_creacion"], reverse=True)
        return archivos
