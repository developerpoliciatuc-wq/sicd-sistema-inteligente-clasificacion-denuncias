"""
Tests para el servicio de sincronización QGIS.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.services.qgis_sync_service import QGISSyncService, PuntoDelito


@pytest.fixture
def temp_sync_dir():
    """Crea un directorio temporal para tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def qgis_service(temp_sync_dir):
    """Crea una instancia del servicio con directorio temporal."""
    return QGISSyncService(temp_sync_dir)


class TestPuntoDelito:
    """Tests para la clase PuntoDelito."""
    
    def test_crear_punto_delito(self):
        """Verifica la creación de un punto de delito."""
        punto = PuntoDelito(
            id="D-123-2025",
            latitud=-26.8241,
            longitud=-65.2226,
            tipo_delito="ROBO",
            modalidad="ARREBATO",
            comisaria="Cria. 1ra",
            fecha_hecho="2025-01-15",
            fecha_registro=datetime.now(),
            direccion="Av. Aconquija 123",
            numero_denuncia="D-123-2025"
        )
        
        assert punto.id == "D-123-2025"
        assert punto.tipo_delito == "ROBO"
        assert punto.latitud == -26.8241
    
    def test_to_geojson_feature(self):
        """Verifica la conversión a GeoJSON Feature."""
        punto = PuntoDelito(
            id="D-123-2025",
            latitud=-26.8241,
            longitud=-65.2226,
            tipo_delito="ROBO",
            modalidad="ARREBATO",
            comisaria="Cria. 1ra",
            fecha_hecho="2025-01-15",
            fecha_registro=datetime.now(),
            direccion="Av. Aconquija 123",
            numero_denuncia="D-123-2025"
        )
        
        feature = punto.to_geojson_feature()
        
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Point"
        # GeoJSON usa [longitud, latitud]
        assert feature["geometry"]["coordinates"] == [-65.2226, -26.8241]
        assert feature["properties"]["tipo_delito"] == "ROBO"
        assert feature["properties"]["color"] == "#FF0000"  # Rojo para ROBO
    
    def test_colores_por_tipo_delito(self):
        """Verifica que cada tipo de delito tenga el color correcto."""
        colores_esperados = {
            "HURTO": "#0000FF",           # Azul
            "ROBO": "#FF0000",            # Rojo
            "ESTAFA": "#FFA500",          # Naranja
            "PORTACION_ARMA_FUEGO": "#000000"  # Negro
        }
        
        for tipo, color_esperado in colores_esperados.items():
            punto = PuntoDelito(
                id="test",
                latitud=-26.0,
                longitud=-65.0,
                tipo_delito=tipo,
                modalidad="",
                comisaria="",
                fecha_hecho="",
                fecha_registro=datetime.now(),
                direccion="",
                numero_denuncia="test"
            )
            feature = punto.to_geojson_feature()
            assert feature["properties"]["color"] == color_esperado


class TestQGISSyncService:
    """Tests para el servicio de sincronización QGIS."""
    
    def test_inicializacion(self, qgis_service, temp_sync_dir):
        """Verifica la inicialización correcta del servicio."""
        # Debe crear el archivo GeoJSON vacío
        archivo = Path(temp_sync_dir) / "denuncias_activas.geojson"
        assert archivo.exists()
        
        # Debe crear la carpeta histórico
        historico = Path(temp_sync_dir) / "historico"
        assert historico.exists()
    
    def test_agregar_denuncia(self, qgis_service, temp_sync_dir):
        """Verifica agregar una denuncia."""
        punto = qgis_service.agregar_denuncia(
            numero_denuncia="D-123-2025",
            latitud=-26.8241,
            longitud=-65.2226,
            tipo_delito="ROBO",
            modalidad="ARREBATO",
            comisaria="Cria. 1ra",
            fecha_hecho="2025-01-15",
            direccion="Av. Aconquija 123"
        )
        
        assert punto.id == "D-123-2025"
        
        # Verificar que se guardó en el archivo
        archivo = Path(temp_sync_dir) / "denuncias_activas.geojson"
        with open(archivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data["features"]) == 1
        assert data["features"][0]["properties"]["numero_denuncia"] == "D-123-2025"
    
    def test_agregar_multiples_denuncias(self, qgis_service):
        """Verifica agregar múltiples denuncias."""
        for i in range(5):
            qgis_service.agregar_denuncia(
                numero_denuncia=f"D-{i}-2025",
                latitud=-26.8241 + i * 0.01,
                longitud=-65.2226,
                tipo_delito="ROBO",
                modalidad="ARREBATO",
                comisaria="Cria. 1ra",
                fecha_hecho="2025-01-15"
            )
        
        puntos = qgis_service.obtener_puntos()
        assert len(puntos) == 5
    
    def test_eliminar_denuncia(self, qgis_service):
        """Verifica eliminar una denuncia."""
        qgis_service.agregar_denuncia(
            numero_denuncia="D-123-2025",
            latitud=-26.8241,
            longitud=-65.2226,
            tipo_delito="ROBO",
            modalidad="ARREBATO",
            comisaria="Cria. 1ra",
            fecha_hecho="2025-01-15"
        )
        
        resultado = qgis_service.eliminar_denuncia("D-123-2025")
        assert resultado is True
        
        # Verificar que ya no existe
        resultado = qgis_service.eliminar_denuncia("D-123-2025")
        assert resultado is False
    
    def test_limpiar_archivo(self, qgis_service):
        """Verifica limpiar todas las denuncias."""
        # Agregar varias denuncias
        for i in range(3):
            qgis_service.agregar_denuncia(
                numero_denuncia=f"D-{i}-2025",
                latitud=-26.8241,
                longitud=-65.2226,
                tipo_delito="ROBO",
                modalidad="ARREBATO",
                comisaria="Cria. 1ra",
                fecha_hecho="2025-01-15"
            )
        
        cantidad = qgis_service.limpiar_archivo()
        assert cantidad == 3
        assert len(qgis_service.obtener_puntos()) == 0
    
    def test_archivar_historico(self, qgis_service, temp_sync_dir):
        """Verifica archivar denuncias en histórico."""
        # Agregar denuncias
        for i in range(3):
            qgis_service.agregar_denuncia(
                numero_denuncia=f"D-{i}-2025",
                latitud=-26.8241,
                longitud=-65.2226,
                tipo_delito="ROBO",
                modalidad="ARREBATO",
                comisaria="Cria. 1ra",
                fecha_hecho="2025-01-15"
            )
        
        # Archivar
        ruta_archivo = qgis_service.archivar_historico()
        
        assert ruta_archivo != ""
        assert Path(ruta_archivo).exists()
        assert len(qgis_service.obtener_puntos()) == 0
    
    def test_obtener_estadisticas(self, qgis_service):
        """Verifica las estadísticas de denuncias."""
        # Agregar denuncias de diferentes tipos
        tipos = ["ROBO", "ROBO", "HURTO", "ESTAFA"]
        for i, tipo in enumerate(tipos):
            qgis_service.agregar_denuncia(
                numero_denuncia=f"D-{i}-2025",
                latitud=-26.8241,
                longitud=-65.2226,
                tipo_delito=tipo,
                modalidad="TEST",
                comisaria="Cria. 1ra",
                fecha_hecho="2025-01-15"
            )
        
        stats = qgis_service.obtener_estadisticas()
        
        assert stats["total_denuncias"] == 4
        assert stats["por_tipo_delito"]["ROBO"] == 2
        assert stats["por_tipo_delito"]["HURTO"] == 1
        assert stats["por_tipo_delito"]["ESTAFA"] == 1
    
    def test_listar_archivos_historicos(self, qgis_service):
        """Verifica listar archivos históricos."""
        # Crear algunos archivos en el histórico
        qgis_service.agregar_denuncia(
            numero_denuncia="D-1-2025",
            latitud=-26.8241,
            longitud=-65.2226,
            tipo_delito="ROBO",
            modalidad="TEST",
            comisaria="Test",
            fecha_hecho="2025-01-15"
        )
        qgis_service.archivar_historico("test1.geojson")
        
        qgis_service.agregar_denuncia(
            numero_denuncia="D-2-2025",
            latitud=-26.8241,
            longitud=-65.2226,
            tipo_delito="HURTO",
            modalidad="TEST",
            comisaria="Test",
            fecha_hecho="2025-01-15"
        )
        qgis_service.archivar_historico("test2.geojson")
        
        archivos = qgis_service.listar_archivos_historicos()
        
        assert len(archivos) >= 2
        nombres = [a["nombre"] for a in archivos]
        assert "test1.geojson" in nombres
        assert "test2.geojson" in nombres
