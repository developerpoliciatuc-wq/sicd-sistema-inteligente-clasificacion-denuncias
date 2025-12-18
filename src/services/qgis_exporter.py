from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.models.denuncia import DenunciaClasificada

logger = logging.getLogger(__name__)

def _normalizar(valor: Any) -> str:
    """Convierte None/vacío a 'NO CONSTA' y todo a string mayúsculas."""
    if valor is None:
        return "NO CONSTA"
    s = str(valor).strip()
    if not s or s.lower() == "null":
        return "NO CONSTA"
    return s.upper()

def exportar_para_qgis(denuncia: DenunciaClasificada, repo_root: Path) -> Path | None:
    """
    Exporta la denuncia al formato plano requerido para el formulario QGIS.
    Guarda en data/qgis_staging/active_denuncia.json
    """
    try:
        staging_dir = repo_root / "data" / "qgis_staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        output_path = staging_dir / "active_denuncia.json"

        # Preparar datos planos
        # Mapeo directo según solicitud del usuario
        
        # Auxiliar para extraer datos anidados de forma segura
        vehiculo = denuncia.vehiculo
        arma = denuncia.arma
        elemento = denuncia.elemento_sustraido
        victima = denuncia.victima
        denunciante = denuncia.denunciante
        causante = denuncia.causante
        dir_hecho = denuncia.direccion_hecho
        
        # Construcción del diccionario plano
        data = {
            "Nº de imagen / sumario o fecha de memorandum": _normalizar(denuncia.numero_sumario),
            
            "Jurisdicción donde tuvo lugar el delito": _normalizar(denuncia.jurisdiccion),
            "Dependencia interviniente": _normalizar(denuncia.comisaria_detectada),
            
            "Fecha del delito": _normalizar(denuncia.fecha),
            "Mes en que ocurrió el delito": _normalizar(denuncia.mes),
            "Día en que ocurrió el hecho": _normalizar(denuncia.dia_semana),
            "Hora del delito": _normalizar(denuncia.hora),
            "Franja horaria en que ocurrió el delito": _normalizar(denuncia.franja_horaria),
            
            "Dirección donde ocurrió el delito": _normalizar(dir_hecho.to_query() if dir_hecho else None),
            "Lugar donde tuvo lugar el delito": _normalizar(denuncia.lugar),
            "Detalle del lugar donde ocurrió el delito": _normalizar(denuncia.detalle_lugar),
            
            "Delito cometido": _normalizar(denuncia.tipo_delito),
            "Modus operandi": _normalizar(denuncia.modalidad_delito),
            
            "Vehículos utilizados": _normalizar(vehiculo.tipo if vehiculo else None),
            "Descripción de los vehículos utilizados": _normalizar(vehiculo.descripcion if vehiculo else None),
            
            "Arma utilizada": _normalizar(arma.tipo if arma else None),
            "Detalle del arma utilizada": _normalizar(arma.detalle if arma else None),
            
            # Truncar a 254 caracteres como solicitado
            "Breve reseña del hecho con los detalles más relevantes HASTA 254 CARACTERES": _normalizar(denuncia.breve_resena)[:254],
            
            "Elemento sustraído": _normalizar(elemento.tipo if elemento else None),
            "Detalle del elemento sustraído": _normalizar(elemento.detalle if elemento else None),
            
            # Victima
            "Apellido y nombre de la víctima": _normalizar(victima.apellido_nombre if victima else None),
            "Sexo de la víctima": _normalizar(victima.sexo if victima else None),
            "Edad de la víctima": _normalizar(victima.edad if victima else None),
            "DNI de la víctima": _normalizar(victima.dni if victima else None),
            "Dirección de la víctima": _normalizar(victima.direccion if victima else None),
            
            # Denunciante
            "Apellido y nombre del denunciante": _normalizar(denunciante.apellido_nombre if denunciante else None),
            "Sexo del denunciante": _normalizar(denunciante.sexo if denunciante else None),
            "Edad del denunciante": _normalizar(denunciante.edad if denunciante else None),
            "DNI del denunciante": _normalizar(denunciante.dni if denunciante else None),
            "Dirección del denunciante": _normalizar(denunciante.direccion if denunciante else None),
            
            "Vínculo denunciante-víctima": _normalizar(denuncia.vinculo_denunciante_victima),
            
            # Causante
            "Apellido y nombre del causante (incluir “alias” si consta)": _normalizar(causante.apellido_nombre if causante else None),
            "Sexo del causante": _normalizar(causante.sexo if causante else None),
            "Edad del causante": _normalizar(causante.edad if causante else None),
            "DNI del causante": _normalizar(causante.dni if causante else None),
            "Dirección del causante": _normalizar(causante.direccion if causante else None),
            "Breve descripción del/de los causante/s": _normalizar(causante.descripcion if causante else None),
            "Situación del causante": _normalizar(causante.situacion if causante else None),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Datos exportados para QGIS en: {output_path}")
        return output_path

    except Exception as e:
        logger.exception(f"Error exportando para QGIS: {e}")
        return None
