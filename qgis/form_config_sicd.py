# -*- coding: utf-8 -*-
"""
Configuración del formulario QGIS para denuncias SICD.
Define los aliases (nombres legibles) para cada campo del GeoJSON.

INSTRUCCIONES:
1. Cargar la capa GeoJSON en QGIS
2. Ejecutar este script en la Consola Python de QGIS
3. Los campos mostrarán nombres legibles en el formulario

Compatible con QGIS 2.14.14+ y QGIS 3.x
"""

# ==============================================================================
# CONFIGURACIÓN DE ALIASES PARA EL FORMULARIO
# ==============================================================================

# Mapeo de campos GeoJSON -> Nombres legibles del formulario policial
ALIASES_FORMULARIO = {
    # Identificación
    "numero_sumario": "Nº de imagen / sumario o fecha de memorandum",
    "numero_denuncia": "Número de denuncia",
    
    # Ubicación institucional
    "jurisdiccion": "Jurisdicción donde tuvo lugar el delito",
    "dependencia": "Dependencia interviniente",
    
    # Temporalidad
    "fecha_hecho": "Fecha del delito",
    "mes": "Mes en que ocurrió el delito",
    "dia_semana": "Día en que ocurrió el hecho",
    "hora": "Hora del delito",
    "franja_horaria": "Franja horaria en que ocurrió el delito",
    
    # Ubicación del hecho
    "direccion": "Dirección donde ocurrió el delito",
    "lugar": "Lugar donde tuvo lugar el delito",
    "detalle_lugar": "Detalle del lugar donde ocurrió el delito",
    
    # Clasificación del delito
    "tipo_delito": "Delito cometido",
    "modalidad": "Modus operandi",
    "breve_resena": "Breve reseña del hecho (máx 254 caracteres)",
    
    # Vehículos
    "vehiculo_utilizado": "Vehículos utilizados",
    "vehiculo_descripcion": "Descripción de los vehículos utilizados",
    
    # Armas
    "arma_utilizada": "Arma utilizada",
    "arma_detalle": "Detalle del arma utilizada",
    
    # Elementos sustraídos
    "elemento_sustraido": "Elemento sustraído",
    "elemento_detalle": "Detalle del elemento sustraído",
    
    # Datos de la víctima
    "victima_nombre": "Apellido y nombre de la víctima",
    "victima_sexo": "Sexo de la víctima",
    "victima_edad": "Edad de la víctima",
    "victima_dni": "DNI de la víctima",
    "victima_direccion": "Dirección de la víctima",
    
    # Datos del denunciante
    "denunciante_nombre": "Apellido y nombre del denunciante",
    "denunciante_sexo": "Sexo del denunciante",
    "denunciante_edad": "Edad del denunciante",
    "denunciante_dni": "DNI del denunciante",
    "denunciante_direccion": "Dirección del denunciante",
    "vinculo_denunciante_victima": "Vínculo denunciante-víctima",
    
    # Datos del causante
    "causante_nombre": "Apellido y nombre del causante (incluir alias)",
    "causante_sexo": "Sexo del causante",
    "causante_edad": "Edad del causante",
    "causante_dni": "DNI del causante",
    "causante_direccion": "Dirección del causante",
    "causante_descripcion": "Breve descripción del/de los causante/s",
    "causante_situacion": "Situación del causante",
    
    # Control interno
    "requiere_revision": "Requiere revisión",
    "motivo_revision": "Motivo de revisión",
    "fecha_registro": "Fecha de registro en sistema",
    "color": "Color de simbología",
    "id": "ID único",
}

# Grupos de campos para organización del formulario
GRUPOS_FORMULARIO = {
    "1. IDENTIFICACIÓN": [
        "numero_sumario",
        "numero_denuncia",
    ],
    "2. UBICACIÓN INSTITUCIONAL": [
        "jurisdiccion",
        "dependencia",
    ],
    "3. TEMPORALIDAD": [
        "fecha_hecho",
        "mes",
        "dia_semana",
        "hora",
        "franja_horaria",
    ],
    "4. UBICACIÓN DEL HECHO": [
        "direccion",
        "lugar",
        "detalle_lugar",
    ],
    "5. CLASIFICACIÓN DEL DELITO": [
        "tipo_delito",
        "modalidad",
        "breve_resena",
    ],
    "6. VEHÍCULOS": [
        "vehiculo_utilizado",
        "vehiculo_descripcion",
    ],
    "7. ARMAS": [
        "arma_utilizada",
        "arma_detalle",
    ],
    "8. ELEMENTOS SUSTRAÍDOS": [
        "elemento_sustraido",
        "elemento_detalle",
    ],
    "9. DATOS DE LA VÍCTIMA": [
        "victima_nombre",
        "victima_sexo",
        "victima_edad",
        "victima_dni",
        "victima_direccion",
    ],
    "10. DATOS DEL DENUNCIANTE": [
        "denunciante_nombre",
        "denunciante_sexo",
        "denunciante_edad",
        "denunciante_dni",
        "denunciante_direccion",
        "vinculo_denunciante_victima",
    ],
    "11. DATOS DEL CAUSANTE": [
        "causante_nombre",
        "causante_sexo",
        "causante_edad",
        "causante_dni",
        "causante_direccion",
        "causante_descripcion",
        "causante_situacion",
    ],
    "12. CONTROL INTERNO": [
        "requiere_revision",
        "motivo_revision",
        "fecha_registro",
    ],
}

# Orden de campos para el formulario (según el formato solicitado)
ORDEN_CAMPOS = [
    "numero_sumario",
    "jurisdiccion",
    "dependencia",
    "fecha_hecho",
    "mes",
    "dia_semana",
    "hora",
    "franja_horaria",
    "direccion",
    "lugar",
    "detalle_lugar",
    "tipo_delito",
    "modalidad",
    "vehiculo_utilizado",
    "vehiculo_descripcion",
    "arma_utilizada",
    "arma_detalle",
    "breve_resena",
    "elemento_sustraido",
    "elemento_detalle",
    "victima_nombre",
    "victima_sexo",
    "victima_edad",
    "victima_dni",
    "victima_direccion",
    "denunciante_nombre",
    "denunciante_sexo",
    "denunciante_edad",
    "denunciante_dni",
    "denunciante_direccion",
    "vinculo_denunciante_victima",
    "causante_nombre",
    "causante_sexo",
    "causante_edad",
    "causante_dni",
    "causante_direccion",
    "causante_descripcion",
    "causante_situacion",
]


# ==============================================================================
# FUNCIONES PARA APLICAR CONFIGURACIÓN EN QGIS
# ==============================================================================

def aplicar_aliases_qgis2(capa):
    """
    Aplica los aliases a una capa en QGIS 2.x.
    
    Args:
        capa: QgsVectorLayer a configurar
    """
    if not capa or not capa.isValid():
        print("[ERROR] Capa no válida")
        return False
    
    campos = capa.pendingFields()
    for i, campo in enumerate(campos):
        nombre = campo.name()
        if nombre in ALIASES_FORMULARIO:
            capa.addAttributeAlias(i, ALIASES_FORMULARIO[nombre])
    
    print(u"[OK] Aliases aplicados a la capa: {}".format(capa.name()))
    return True


def aplicar_aliases_qgis3(capa):
    """
    Aplica los aliases a una capa en QGIS 3.x.
    
    Args:
        capa: QgsVectorLayer a configurar
    """
    if not capa or not capa.isValid():
        print("[ERROR] Capa no válida")
        return False
    
    for nombre_campo, alias in ALIASES_FORMULARIO.items():
        idx = capa.fields().indexFromName(nombre_campo)
        if idx >= 0:
            capa.setFieldAlias(idx, alias)
    
    print(f"[OK] Aliases aplicados a la capa: {capa.name()}")
    return True


def configurar_formulario_capa(nombre_capa="Denuncias SICD"):
    """
    Busca una capa por nombre y aplica la configuración del formulario.
    
    Args:
        nombre_capa: Nombre de la capa en QGIS
    """
    try:
        # Intentar QGIS 3.x primero
        from qgis.core import QgsProject
        capas = QgsProject.instance().mapLayersByName(nombre_capa)
        if capas:
            return aplicar_aliases_qgis3(capas[0])
    except ImportError:
        pass
    
    try:
        # QGIS 2.x
        from qgis.core import QgsMapLayerRegistry
        capas = QgsMapLayerRegistry.instance().mapLayersByName(nombre_capa)
        if capas:
            return aplicar_aliases_qgis2(capas[0])
    except ImportError:
        pass
    
    print(u"[ERROR] No se encontró la capa: {}".format(nombre_capa))
    return False


def generar_texto_formulario_vacio():
    """
    Genera el texto del formulario vacío con todos los campos.
    Útil para copiar y pegar.
    """
    lineas = []
    for campo in ORDEN_CAMPOS:
        alias = ALIASES_FORMULARIO.get(campo, campo)
        lineas.append(u"{}:\n".format(alias))
    
    texto = u"\n".join(lineas)
    texto += u"\n📋 Instrucción final:\n"
    texto += u'Si algún campo aparece vacío o con el valor "NULL", indícalo como "NO CONSTA".\n'
    texto += u"\nRespeta exactamente el orden"
    
    return texto


# ==============================================================================
# EJECUCIÓN DIRECTA
# ==============================================================================

if __name__ == "__main__":
    # Si se ejecuta directamente en la consola de QGIS
    print("=" * 60)
    print("SICD - Configuración de Formulario QGIS")
    print("=" * 60)
    
    # Aplicar configuración a la capa de denuncias
    configurar_formulario_capa("Denuncias SICD")
    
    print("-" * 60)
    print("Formulario vacío para referencia:")
    print("-" * 60)
    print(generar_texto_formulario_vacio())
