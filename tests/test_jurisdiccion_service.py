"""
Tests para el servicio de validación de jurisdicciones.
"""

import json
import tempfile
from pathlib import Path

import pytest

from src.services.jurisdiccion_service import (
    JurisdiccionService,
    ResultadoValidacion,
    GEOPANDAS_DISPONIBLE
)


@pytest.fixture
def config_file():
    """Crea un archivo de configuración temporal."""
    config = {
        "unidad_red": "Z:",
        "ruta_base": "MAPA DEL DELITO/MAPAS DEL DELITO POR JURISDICCIONES",
        "unidades_regionales": {
            "URC": {
                "nombre": "Unidad Regional Capital",
                "comisarias": {
                    "CRIA1": "CRIA1-URC-2020/test.shp",
                    "CRIA2": "CRIA2-URC-2020/test.shp"
                }
            },
            "URN": {
                "nombre": "Unidad Regional Norte",
                "comisarias": {
                    "YERBA_BUENA": "YERBA_BUENA/test.shp"
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)
        return f.name


@pytest.fixture
def jurisdiccion_service(config_file):
    """Crea una instancia del servicio con configuración de prueba."""
    return JurisdiccionService(config_file)


class TestJurisdiccionService:
    """Tests para el servicio de jurisdicción."""
    
    def test_cargar_configuracion(self, jurisdiccion_service):
        """Verifica que la configuración se carga correctamente."""
        assert jurisdiccion_service.config is not None
        assert "unidades_regionales" in jurisdiccion_service.config
    
    def test_obtener_todas_comisarias(self, jurisdiccion_service):
        """Verifica obtener todas las comisarías configuradas."""
        comisarias = jurisdiccion_service.obtener_todas_comisarias()
        
        assert "URC" in comisarias
        assert "URN" in comisarias
        assert "CRIA1" in comisarias["URC"]["comisarias"]
        assert "YERBA_BUENA" in comisarias["URN"]["comisarias"]
    
    def test_obtener_info_estado(self, jurisdiccion_service):
        """Verifica obtener información del estado del servicio."""
        info = jurisdiccion_service.obtener_info_estado()
        
        assert "geopandas_disponible" in info
        assert "unidad_red_disponible" in info
        assert "servicio_operativo" in info
        assert "total_comisarias_configuradas" in info
        assert info["total_comisarias_configuradas"] == 3  # 2 URC + 1 URN
    
    def test_normalizar_nombre_comisaria(self, jurisdiccion_service):
        """Verifica la normalización de nombres de comisaría."""
        casos = [
            ("Comisaria YERBA BUENA-URN", "YERBA BUENA"),
            ("Cria. 1ra-URC", "1RA"),
            ("CRIA LULES-URO", "LULES"),
            ("Subcomisaria de Tapia-URN", "DE TAPIA"),
        ]
        
        for entrada, esperado in casos:
            resultado = jurisdiccion_service._normalizar_nombre_comisaria(entrada)
            assert resultado == esperado, f"'{entrada}' debería ser '{esperado}', pero fue '{resultado}'"
    
    def test_validacion_sin_red_disponible(self, jurisdiccion_service):
        """Verifica que la validación funciona cuando la red no está disponible."""
        # Forzar que el servicio no esté disponible
        jurisdiccion_service._unidad_red_disponible = False
        
        resultado = jurisdiccion_service.validar_jurisdiccion(
            latitud=-26.8241,
            longitud=-65.2226,
            comisaria_denuncia="Cria. 1ra"
        )

        assert isinstance(resultado, ResultadoValidacion)
        # Cuando no está disponible, asume válido
        assert resultado.es_valido is True
        assert "no accesible" in resultado.mensaje
        """Verifica refrescar el estado de disponibilidad."""
        resultado = jurisdiccion_service.refrescar_disponibilidad()
        # El resultado depende de si la unidad Z: está montada
        assert isinstance(resultado, bool)
    
    def test_limpiar_cache(self, jurisdiccion_service):
        """Verifica limpiar el cache de shapefiles."""
        # Agregar algo al cache
        jurisdiccion_service._cache_shapefiles["test"] = "data"
        
        jurisdiccion_service.limpiar_cache()
        
        assert len(jurisdiccion_service._cache_shapefiles) == 0


class TestResultadoValidacion:
    """Tests para la clase ResultadoValidacion."""
    
    def test_crear_resultado_valido(self):
        """Verifica crear un resultado de validación válido."""
        resultado = ResultadoValidacion(
            es_valido=True,
            comisaria_esperada="Cria. 1ra",
            comisaria_real="CRIA1",
            distancia_km=0,
            mensaje="La ubicación corresponde a la jurisdicción correcta",
            jurisdicciones_cercanas=[]
        )
        
        assert resultado.es_valido is True
        assert resultado.comisaria_esperada == "Cria. 1ra"
    
    def test_crear_resultado_invalido(self):
        """Verifica crear un resultado de validación inválido."""
        resultado = ResultadoValidacion(
            es_valido=False,
            comisaria_esperada="Cria. 1ra",
            comisaria_real="CRIA2",
            distancia_km=None,
            mensaje="La ubicación corresponde a CRIA2, no a Cria. 1ra",
            jurisdicciones_cercanas=["CRIA2"]
        )
        
        assert resultado.es_valido is False
        assert "CRIA2" in resultado.jurisdicciones_cercanas


@pytest.mark.skipif(not GEOPANDAS_DISPONIBLE, reason="geopandas no instalado")
class TestJurisdiccionServiceConGeopandas:
    """Tests que requieren geopandas instalado."""
    
    def test_geopandas_disponible(self):
        """Verifica que geopandas está disponible."""
        import geopandas
        assert geopandas is not None
    
    def test_servicio_detecta_geopandas(self, jurisdiccion_service):
        """Verifica que el servicio detecta geopandas."""
        info = jurisdiccion_service.obtener_info_estado()
        assert info["geopandas_disponible"] is True
