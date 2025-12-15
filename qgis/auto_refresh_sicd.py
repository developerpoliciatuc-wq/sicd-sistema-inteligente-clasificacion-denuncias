# -*- coding: utf-8 -*-
"""
Script de auto-actualización para QGIS 2.14.14 (Essen)
Monitorea el archivo GeoJSON de denuncias y actualiza la capa automáticamente.

INSTRUCCIONES DE USO:
1. Abrir QGIS 2.14.14
2. Ir a Complementos > Consola de Python
3. Copiar y pegar este script completo
4. El script comenzará a monitorear automáticamente

NOTA: Este script está diseñado para QGIS 2.14.14 con PyQt4.
Para versiones más nuevas de QGIS (3.x), se requieren modificaciones.
"""

from PyQt4.QtCore import QTimer, QFileInfo
from PyQt4.QtGui import QColor
from qgis.core import (
    QgsVectorLayer, 
    QgsMapLayerRegistry,
    QgsSymbolV2,
    QgsCategorizedSymbolRendererV2,
    QgsRendererCategoryV2,
    QgsMarkerSymbolV2
)
import os


# ============================================================================
# CONFIGURACIÓN - AJUSTAR SEGÚN NECESIDAD
# ============================================================================

# Ruta al archivo GeoJSON generado por SICD
# Cambiar esta ruta a la ubicación real en tu sistema
RUTA_GEOJSON = r"C:\Users\Usuario\OneDrive\Desktop\SICD\data\OUTPUT\QGIS_SYNC\denuncias_activas.geojson"

# Intervalo de actualización en milisegundos (5000 = 5 segundos)
INTERVALO_ACTUALIZACION = 5000

# Nombre de la capa en QGIS
NOMBRE_CAPA = "Denuncias SICD"

# Colores por tipo de delito
COLORES_DELITOS = {
    "HURTO": "#0000FF",           # Azul
    "ROBO": "#FF0000",            # Rojo
    "ESTAFA": "#FFA500",          # Naranja
    "PORTACION_ARMA_FUEGO": "#000000"  # Negro
}

# Tamaño de los marcadores
TAMANO_MARCADOR = 4


# ============================================================================
# CLASE PRINCIPAL DE MONITOREO
# ============================================================================

class MonitorSICD:
    """Monitor de archivos GeoJSON para sincronización con SICD."""
    
    def __init__(self, ruta_geojson, intervalo=5000):
        """
        Inicializa el monitor.
        
        Args:
            ruta_geojson: Ruta al archivo GeoJSON
            intervalo: Intervalo de actualización en milisegundos
        """
        self.ruta_geojson = ruta_geojson
        self.intervalo = intervalo
        self.ultima_modificacion = None
        self.capa_actual = None
        self.timer = None
        
        print("=" * 60)
        print("SICD Monitor para QGIS 2.14.14")
        print("=" * 60)
        print(u"Archivo monitoreado: {}".format(self.ruta_geojson))
        print(u"Intervalo de actualizacion: {} ms".format(self.intervalo))
        print("=" * 60)
    
    def iniciar(self):
        """Inicia el monitoreo del archivo."""
        # Cargar capa inicial
        self._cargar_capa()
        
        # Configurar timer para actualizaciones
        self.timer = QTimer()
        self.timer.timeout.connect(self._verificar_cambios)
        self.timer.start(self.intervalo)
        
        print(u"[SICD] Monitoreo iniciado. Verificando cada {} segundos.".format(
            self.intervalo / 1000))
    
    def detener(self):
        """Detiene el monitoreo."""
        if self.timer:
            self.timer.stop()
            self.timer = None
        print("[SICD] Monitoreo detenido.")
    
    def _verificar_cambios(self):
        """Verifica si el archivo ha cambiado y actualiza la capa."""
        if not os.path.exists(self.ruta_geojson):
            return
        
        # Obtener fecha de modificación
        info = QFileInfo(self.ruta_geojson)
        modificacion = info.lastModified()
        
        # Comparar con última modificación conocida
        if self.ultima_modificacion is None or modificacion > self.ultima_modificacion:
            self.ultima_modificacion = modificacion
            self._actualizar_capa()
    
    def _cargar_capa(self):
        """Carga la capa GeoJSON por primera vez."""
        if not os.path.exists(self.ruta_geojson):
            print(u"[SICD] ERROR: Archivo no encontrado: {}".format(self.ruta_geojson))
            print("[SICD] Esperando a que SICD genere el archivo...")
            return
        
        # Crear capa vectorial desde GeoJSON
        uri = self.ruta_geojson
        self.capa_actual = QgsVectorLayer(uri, NOMBRE_CAPA, "ogr")
        
        if not self.capa_actual.isValid():
            print("[SICD] ERROR: No se pudo cargar la capa. Verificar ruta del archivo.")
            return
        
        # Aplicar simbología categorizada
        self._aplicar_simbologia()
        
        # Agregar al registro de capas
        QgsMapLayerRegistry.instance().addMapLayer(self.capa_actual)
        
        # Guardar fecha de modificación
        info = QFileInfo(self.ruta_geojson)
        self.ultima_modificacion = info.lastModified()
        
        print(u"[SICD] Capa cargada: {} features".format(
            self.capa_actual.featureCount()))
    
    def _actualizar_capa(self):
        """Actualiza la capa con los nuevos datos."""
        if self.capa_actual is None:
            self._cargar_capa()
            return
        
        # Obtener cantidad anterior
        cantidad_anterior = self.capa_actual.featureCount()
        
        # Recargar datos del proveedor
        self.capa_actual.dataProvider().reloadData()
        self.capa_actual.updateExtents()
        self.capa_actual.triggerRepaint()
        
        # Obtener nueva cantidad
        cantidad_nueva = self.capa_actual.featureCount()
        
        # Mostrar mensaje solo si hay cambios
        if cantidad_nueva != cantidad_anterior:
            print(u"[SICD] Capa actualizada: {} -> {} features".format(
                cantidad_anterior, cantidad_nueva))
    
    def _aplicar_simbologia(self):
        """Aplica simbología categorizada por tipo de delito."""
        if self.capa_actual is None:
            return
        
        # Crear categorías
        categorias = []
        
        for tipo_delito, color_hex in COLORES_DELITOS.items():
            # Crear símbolo de marcador
            simbolo = QgsMarkerSymbolV2.createSimple({
                'name': 'circle',
                'color': color_hex,
                'size': str(TAMANO_MARCADOR),
                'outline_color': '#000000',
                'outline_width': '0.5'
            })
            
            # Crear categoría
            categoria = QgsRendererCategoryV2(
                tipo_delito,  # Valor
                simbolo,      # Símbolo
                tipo_delito   # Etiqueta
            )
            categorias.append(categoria)
        
        # Agregar categoría para valores desconocidos
        simbolo_otro = QgsMarkerSymbolV2.createSimple({
            'name': 'circle',
            'color': '#808080',  # Gris
            'size': str(TAMANO_MARCADOR),
            'outline_color': '#000000',
            'outline_width': '0.5'
        })
        categoria_otro = QgsRendererCategoryV2(
            '',           # Valor vacío para "otros"
            simbolo_otro,
            'Otro'
        )
        categorias.append(categoria_otro)
        
        # Crear renderizador categorizado
        campo = 'tipo_delito'
        renderizador = QgsCategorizedSymbolRendererV2(campo, categorias)
        
        # Aplicar a la capa
        self.capa_actual.setRendererV2(renderizador)
        
        print("[SICD] Simbologia aplicada por tipo de delito.")
    
    def forzar_actualizacion(self):
        """Fuerza una actualización inmediata de la capa."""
        self._actualizar_capa()
        print("[SICD] Actualizacion forzada completada.")
    
    def zoom_a_denuncias(self):
        """Hace zoom al extent de las denuncias."""
        if self.capa_actual and self.capa_actual.featureCount() > 0:
            iface.mapCanvas().setExtent(self.capa_actual.extent())
            iface.mapCanvas().refresh()
            print("[SICD] Zoom aplicado al extent de denuncias.")


# ============================================================================
# INICIALIZACIÓN AUTOMÁTICA
# ============================================================================

# Crear instancia global del monitor
monitor_sicd = MonitorSICD(RUTA_GEOJSON, INTERVALO_ACTUALIZACION)

# Iniciar monitoreo
monitor_sicd.iniciar()

# Imprimir comandos disponibles
print("")
print("COMANDOS DISPONIBLES:")
print("  monitor_sicd.detener()           - Detener monitoreo")
print("  monitor_sicd.iniciar()           - Reiniciar monitoreo")
print("  monitor_sicd.forzar_actualizacion() - Forzar actualizacion")
print("  monitor_sicd.zoom_a_denuncias()  - Zoom al extent de denuncias")
print("")
