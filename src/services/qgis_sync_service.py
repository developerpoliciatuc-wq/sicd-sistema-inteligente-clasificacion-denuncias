"""
Servicio de sincronización en tiempo real con QGIS.
Genera archivos GeoJSON que QGIS puede monitorear para actualización automática.
También escribe directamente a los shapefiles de la red.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
import logging

from src.models.denuncia import NO_CONSTA

logger = logging.getLogger(__name__)

# Importar el servicio de escritura de shapefiles
try:
    from src.services.shapefile_writer_service import ShapefileWriterService
    SHAPEFILE_WRITER_DISPONIBLE = True
except ImportError:
    try:
        from services.shapefile_writer_service import ShapefileWriterService
        SHAPEFILE_WRITER_DISPONIBLE = True
    except ImportError:
        SHAPEFILE_WRITER_DISPONIBLE = False
        logger.warning("ShapefileWriterService no disponible")


@dataclass
class PuntoDelito:
    """Representa un punto de delito georreferenciado con todos los campos del formulario."""
    
    # --- Identificación ---
    id: str
    numero_denuncia: str
    numero_sumario: str = NO_CONSTA
    
    # --- Coordenadas ---
    latitud: float = 0.0
    longitud: float = 0.0
    
    # --- Institución ---
    jurisdiccion: str = NO_CONSTA
    dependencia: str = NO_CONSTA  # comisaria
    
    # --- Temporalidad ---
    fecha_hecho: str = NO_CONSTA
    mes: str = NO_CONSTA
    dia_semana: str = NO_CONSTA
    hora: str = NO_CONSTA
    franja_horaria: str = "#NO_CONSTA"
    fecha_registro: datetime = field(default_factory=datetime.now)
    
    # --- Ubicación del hecho ---
    direccion: str = NO_CONSTA
    lugar: str = NO_CONSTA
    detalle_lugar: str = NO_CONSTA
    
    # --- Clasificación del delito ---
    tipo_delito: str = NO_CONSTA
    modalidad: str = NO_CONSTA
    breve_resena: str = NO_CONSTA
    
    # --- Vehículos ---
    vehiculo_utilizado: str = NO_CONSTA
    vehiculo_descripcion: str = NO_CONSTA
    
    # --- Armas ---
    arma_utilizada: str = NO_CONSTA
    arma_detalle: str = NO_CONSTA
    
    # --- Elementos sustraídos ---
    elemento_sustraido: str = NO_CONSTA
    elemento_detalle: str = NO_CONSTA
    
    # --- Datos de la víctima ---
    victima_nombre: str = NO_CONSTA
    victima_sexo: str = NO_CONSTA
    victima_edad: str = NO_CONSTA
    victima_dni: str = NO_CONSTA
    victima_direccion: str = NO_CONSTA
    
    # --- Datos del denunciante ---
    denunciante_nombre: str = NO_CONSTA
    denunciante_sexo: str = NO_CONSTA
    denunciante_edad: str = NO_CONSTA
    denunciante_dni: str = NO_CONSTA
    denunciante_direccion: str = NO_CONSTA
    vinculo_denunciante_victima: str = NO_CONSTA
    
    # --- Datos del causante ---
    causante_nombre: str = NO_CONSTA
    causante_sexo: str = NO_CONSTA
    causante_edad: str = NO_CONSTA
    causante_dni: str = NO_CONSTA
    causante_direccion: str = NO_CONSTA
    causante_descripcion: str = NO_CONSTA
    causante_situacion: str = NO_CONSTA
    
    # --- Control ---
    requiere_revision: str = "NO"
    motivo_revision: str = NO_CONSTA
    
    def to_geojson_feature(self) -> Dict[str, Any]:
        """Convierte el punto a un Feature GeoJSON con todos los campos del formulario."""
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitud, self.latitud]  # GeoJSON usa [lng, lat]
            },
            "properties": {
                # Identificación
                "id": self.id,
                "numero_denuncia": self.numero_denuncia,
                "numero_sumario": self.numero_sumario,
                
                # Institución
                "jurisdiccion": self.jurisdiccion,
                "dependencia": self.dependencia,
                
                # Temporalidad
                "fecha_hecho": self.fecha_hecho,
                "mes": self.mes,
                "dia_semana": self.dia_semana,
                "hora": self.hora,
                "franja_horaria": self.franja_horaria,
                "fecha_registro": self.fecha_registro.isoformat() if isinstance(self.fecha_registro, datetime) else self.fecha_registro,
                
                # Ubicación
                "direccion": self.direccion,
                "lugar": self.lugar,
                "detalle_lugar": self.detalle_lugar,
                
                # Delito
                "tipo_delito": self.tipo_delito,
                "modalidad": self.modalidad,
                "breve_resena": self.breve_resena,
                
                # Vehículos
                "vehiculo_utilizado": self.vehiculo_utilizado,
                "vehiculo_descripcion": self.vehiculo_descripcion,
                
                # Armas
                "arma_utilizada": self.arma_utilizada,
                "arma_detalle": self.arma_detalle,
                
                # Elementos
                "elemento_sustraido": self.elemento_sustraido,
                "elemento_detalle": self.elemento_detalle,
                
                # Víctima
                "victima_nombre": self.victima_nombre,
                "victima_sexo": self.victima_sexo,
                "victima_edad": self.victima_edad,
                "victima_dni": self.victima_dni,
                "victima_direccion": self.victima_direccion,
                
                # Denunciante
                "denunciante_nombre": self.denunciante_nombre,
                "denunciante_sexo": self.denunciante_sexo,
                "denunciante_edad": self.denunciante_edad,
                "denunciante_dni": self.denunciante_dni,
                "denunciante_direccion": self.denunciante_direccion,
                "vinculo_denunciante_victima": self.vinculo_denunciante_victima,
                
                # Causante
                "causante_nombre": self.causante_nombre,
                "causante_sexo": self.causante_sexo,
                "causante_edad": self.causante_edad,
                "causante_dni": self.causante_dni,
                "causante_direccion": self.causante_direccion,
                "causante_descripcion": self.causante_descripcion,
                "causante_situacion": self.causante_situacion,
                
                # Control
                "requiere_revision": self.requiere_revision,
                "motivo_revision": self.motivo_revision,
                
                # Color para simbología
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
    También escribe directamente a los shapefiles de la red Z:.
    
    Soporta:
    - Actualización en tiempo real de puntos
    - Escritura directa a shapefiles por comisaría
    - Archivo histórico manual
    - Estadísticas de delitos
    """
    
    ARCHIVO_ACTIVO = "denuncias_activas.geojson"
    CARPETA_HISTORICO = "historico"
    
    def __init__(self, ruta_sync: str, escribir_shapefiles: bool = True):
        """
        Inicializa el servicio de sincronización.
        
        Args:
            ruta_sync: Ruta a la carpeta de sincronización QGIS (ej: data/OUTPUT/QGIS_SYNC)
            escribir_shapefiles: Si True, también escribe a los shapefiles de la red
        """
        self.ruta_sync = Path(ruta_sync)
        self.ruta_archivo_activo = self.ruta_sync / self.ARCHIVO_ACTIVO
        self.ruta_historico = self.ruta_sync / self.CARPETA_HISTORICO
        self.escribir_shapefiles = escribir_shapefiles
        
        # Inicializar puntos vacío ANTES de inicializar estructura
        self._puntos: Dict[str, PuntoDelito] = {}
        
        # Inicializar servicio de escritura de shapefiles
        self._shapefile_writer: Optional[ShapefileWriterService] = None
        if escribir_shapefiles and SHAPEFILE_WRITER_DISPONIBLE:
            try:
                self._shapefile_writer = ShapefileWriterService()
                logger.info("ShapefileWriterService inicializado correctamente")
            except Exception as e:
                logger.warning(f"No se pudo inicializar ShapefileWriterService: {e}")
        
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
                
                # Parsear fecha_registro
                fecha_reg_str = props.get('fecha_registro', datetime.now().isoformat())
                try:
                    fecha_registro = datetime.fromisoformat(fecha_reg_str)
                except:
                    fecha_registro = datetime.now()
                
                punto = PuntoDelito(
                    # Identificación
                    id=props.get('id', ''),
                    numero_denuncia=props.get('numero_denuncia', props.get('id', '')),
                    numero_sumario=props.get('numero_sumario', NO_CONSTA),
                    
                    # Coordenadas
                    latitud=coords[1],  # GeoJSON: [lng, lat]
                    longitud=coords[0],
                    
                    # Institución
                    jurisdiccion=props.get('jurisdiccion', NO_CONSTA),
                    dependencia=props.get('dependencia', props.get('comisaria', NO_CONSTA)),
                    
                    # Temporalidad
                    fecha_hecho=props.get('fecha_hecho', NO_CONSTA),
                    mes=props.get('mes', NO_CONSTA),
                    dia_semana=props.get('dia_semana', NO_CONSTA),
                    hora=props.get('hora', NO_CONSTA),
                    franja_horaria=props.get('franja_horaria', '#NO_CONSTA'),
                    fecha_registro=fecha_registro,
                    
                    # Ubicación
                    direccion=props.get('direccion', NO_CONSTA),
                    lugar=props.get('lugar', NO_CONSTA),
                    detalle_lugar=props.get('detalle_lugar', NO_CONSTA),
                    
                    # Delito
                    tipo_delito=props.get('tipo_delito', NO_CONSTA),
                    modalidad=props.get('modalidad', NO_CONSTA),
                    breve_resena=props.get('breve_resena', NO_CONSTA),
                    
                    # Vehículos
                    vehiculo_utilizado=props.get('vehiculo_utilizado', NO_CONSTA),
                    vehiculo_descripcion=props.get('vehiculo_descripcion', NO_CONSTA),
                    
                    # Armas
                    arma_utilizada=props.get('arma_utilizada', NO_CONSTA),
                    arma_detalle=props.get('arma_detalle', NO_CONSTA),
                    
                    # Elementos
                    elemento_sustraido=props.get('elemento_sustraido', NO_CONSTA),
                    elemento_detalle=props.get('elemento_detalle', NO_CONSTA),
                    
                    # Víctima
                    victima_nombre=props.get('victima_nombre', NO_CONSTA),
                    victima_sexo=props.get('victima_sexo', NO_CONSTA),
                    victima_edad=props.get('victima_edad', NO_CONSTA),
                    victima_dni=props.get('victima_dni', NO_CONSTA),
                    victima_direccion=props.get('victima_direccion', NO_CONSTA),
                    
                    # Denunciante
                    denunciante_nombre=props.get('denunciante_nombre', NO_CONSTA),
                    denunciante_sexo=props.get('denunciante_sexo', NO_CONSTA),
                    denunciante_edad=props.get('denunciante_edad', NO_CONSTA),
                    denunciante_dni=props.get('denunciante_dni', NO_CONSTA),
                    denunciante_direccion=props.get('denunciante_direccion', NO_CONSTA),
                    vinculo_denunciante_victima=props.get('vinculo_denunciante_victima', NO_CONSTA),
                    
                    # Causante
                    causante_nombre=props.get('causante_nombre', NO_CONSTA),
                    causante_sexo=props.get('causante_sexo', NO_CONSTA),
                    causante_edad=props.get('causante_edad', NO_CONSTA),
                    causante_dni=props.get('causante_dni', NO_CONSTA),
                    causante_direccion=props.get('causante_direccion', NO_CONSTA),
                    causante_descripcion=props.get('causante_descripcion', NO_CONSTA),
                    causante_situacion=props.get('causante_situacion', NO_CONSTA),
                    
                    # Control
                    requiere_revision=props.get('requiere_revision', 'NO'),
                    motivo_revision=props.get('motivo_revision', NO_CONSTA),
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
        direccion: str = "",
        # Nuevos campos del formulario completo
        numero_sumario: str = None,
        jurisdiccion: str = None,
        mes: str = None,
        dia_semana: str = None,
        hora: str = None,
        franja_horaria: str = None,
        lugar: str = None,
        detalle_lugar: str = None,
        breve_resena: str = None,
        vehiculo_utilizado: str = None,
        vehiculo_descripcion: str = None,
        arma_utilizada: str = None,
        arma_detalle: str = None,
        elemento_sustraido: str = None,
        elemento_detalle: str = None,
        victima_nombre: str = None,
        victima_sexo: str = None,
        victima_edad: str = None,
        victima_dni: str = None,
        victima_direccion: str = None,
        denunciante_nombre: str = None,
        denunciante_sexo: str = None,
        denunciante_edad: str = None,
        denunciante_dni: str = None,
        denunciante_direccion: str = None,
        vinculo_denunciante_victima: str = None,
        causante_nombre: str = None,
        causante_sexo: str = None,
        causante_edad: str = None,
        causante_dni: str = None,
        causante_direccion: str = None,
        causante_descripcion: str = None,
        causante_situacion: str = None,
        requiere_revision: bool = False,
        motivo_revision: str = None,
    ) -> PuntoDelito:
        """
        Agrega una nueva denuncia al mapa con todos los campos del formulario QGIS.
        
        Args:
            numero_denuncia: Número de denuncia (ej: "D-563745-2025")
            latitud: Latitud del hecho
            longitud: Longitud del hecho
            tipo_delito: Tipo de delito (ROBO, HURTO, ESTAFA, PORTACION_ARMA_FUEGO)
            modalidad: Modalidad del delito
            comisaria: Comisaría que recibió la denuncia
            fecha_hecho: Fecha del hecho
            direccion: Dirección del hecho
            [... campos adicionales del formulario ...]
            
        Returns:
            PuntoDelito creado
        """
        punto = PuntoDelito(
            # Identificación
            id=numero_denuncia,
            numero_denuncia=numero_denuncia,
            numero_sumario=numero_sumario or NO_CONSTA,
            
            # Coordenadas
            latitud=latitud,
            longitud=longitud,
            
            # Institución
            jurisdiccion=jurisdiccion or NO_CONSTA,
            dependencia=comisaria or NO_CONSTA,
            
            # Temporalidad
            fecha_hecho=fecha_hecho or NO_CONSTA,
            mes=mes or NO_CONSTA,
            dia_semana=dia_semana or NO_CONSTA,
            hora=hora or NO_CONSTA,
            franja_horaria=franja_horaria or "#NO_CONSTA",
            fecha_registro=datetime.now(),
            
            # Ubicación
            direccion=direccion or NO_CONSTA,
            lugar=lugar or NO_CONSTA,
            detalle_lugar=detalle_lugar or NO_CONSTA,
            
            # Delito
            tipo_delito=tipo_delito or NO_CONSTA,
            modalidad=modalidad or NO_CONSTA,
            breve_resena=breve_resena or NO_CONSTA,
            
            # Vehículos
            vehiculo_utilizado=vehiculo_utilizado or NO_CONSTA,
            vehiculo_descripcion=vehiculo_descripcion or NO_CONSTA,
            
            # Armas
            arma_utilizada=arma_utilizada or NO_CONSTA,
            arma_detalle=arma_detalle or NO_CONSTA,
            
            # Elementos
            elemento_sustraido=elemento_sustraido or NO_CONSTA,
            elemento_detalle=elemento_detalle or NO_CONSTA,
            
            # Víctima
            victima_nombre=victima_nombre or NO_CONSTA,
            victima_sexo=victima_sexo or NO_CONSTA,
            victima_edad=victima_edad or NO_CONSTA,
            victima_dni=victima_dni or NO_CONSTA,
            victima_direccion=victima_direccion or NO_CONSTA,
            
            # Denunciante
            denunciante_nombre=denunciante_nombre or NO_CONSTA,
            denunciante_sexo=denunciante_sexo or NO_CONSTA,
            denunciante_edad=denunciante_edad or NO_CONSTA,
            denunciante_dni=denunciante_dni or NO_CONSTA,
            denunciante_direccion=denunciante_direccion or NO_CONSTA,
            vinculo_denunciante_victima=vinculo_denunciante_victima or NO_CONSTA,
            
            # Causante
            causante_nombre=causante_nombre or NO_CONSTA,
            causante_sexo=causante_sexo or NO_CONSTA,
            causante_edad=causante_edad or NO_CONSTA,
            causante_dni=causante_dni or NO_CONSTA,
            causante_direccion=causante_direccion or NO_CONSTA,
            causante_descripcion=causante_descripcion or NO_CONSTA,
            causante_situacion=causante_situacion or NO_CONSTA,
            
            # Control
            requiere_revision="SI" if requiere_revision else "NO",
            motivo_revision=motivo_revision or NO_CONSTA,
        )
        
        self._puntos[punto.id] = punto
        self._guardar_geojson()
        
        # Escribir también al shapefile de la red
        resultado_shapefile = self._escribir_a_shapefile(
            comisaria=comisaria,
            latitud=latitud,
            longitud=longitud,
            tipo_delito=tipo_delito,
            modalidad=modalidad,
            numero_denuncia=numero_denuncia,
            fecha_hecho=fecha_hecho,
            direccion=direccion
        )
        
        logger.info(f"Denuncia agregada al mapa: {numero_denuncia} ({tipo_delito} - {modalidad})")
        if resultado_shapefile:
            logger.info(f"Shapefile: {resultado_shapefile}")
        
        return punto
    
    def _escribir_a_shapefile(
        self,
        comisaria: str,
        latitud: float,
        longitud: float,
        tipo_delito: str,
        modalidad: str,
        numero_denuncia: str,
        fecha_hecho: str,
        direccion: str
    ) -> str:
        """
        Escribe el punto al shapefile correspondiente en la red.
        
        Returns:
            Mensaje de resultado
        """
        if not self._shapefile_writer:
            return "ShapefileWriter no disponible"
        
        try:
            exito, mensaje = self._shapefile_writer.agregar_punto_a_shapefile(
                comisaria=comisaria,
                latitud=latitud,
                longitud=longitud,
                tipo_delito=tipo_delito,
                modalidad=modalidad,
                numero_denuncia=numero_denuncia,
                fecha_hecho=fecha_hecho,
                direccion=direccion
            )
            
            if exito:
                logger.info(f"✓ Punto guardado en shapefile: {mensaje}")
            else:
                logger.warning(f"✗ No se pudo guardar en shapefile: {mensaje}")
            
            return mensaje
        except Exception as e:
            error_msg = f"Error escribiendo a shapefile: {e}"
            logger.error(error_msg)
            return error_msg
    
    def verificar_conexion_red(self) -> tuple:
        """
        Verifica si la unidad de red Z: está accesible.
        
        Returns:
            Tupla (conectado: bool, mensaje: str)
        """
        if not self._shapefile_writer:
            return False, "ShapefileWriter no disponible"
        
        return self._shapefile_writer.verificar_conexion_red()
    
    def obtener_ruta_shapefile_comisaria(self, comisaria: str) -> str:
        """
        Obtiene la ruta del shapefile para una comisaría específica.
        
        Args:
            comisaria: Nombre de la comisaría
            
        Returns:
            Ruta al shapefile o mensaje de error
        """
        if not self._shapefile_writer:
            return "ShapefileWriter no disponible"
        
        ruta = self._shapefile_writer.obtener_ruta_shapefile(comisaria)
        return ruta if ruta else f"No se encontró shapefile para: {comisaria}"
    
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
            
            # Por comisaría (ahora es 'dependencia')
            stats["por_comisaria"][punto.dependencia] = \
                stats["por_comisaria"].get(punto.dependencia, 0) + 1
            
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
