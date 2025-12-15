# Integración QGIS - SICD

Este directorio contiene los archivos necesarios para la integración en tiempo real entre SICD y QGIS 2.14.14.

## Archivos

- **`auto_refresh_sicd.py`**: Script de Python para QGIS que monitorea el archivo GeoJSON y actualiza la capa automáticamente.
- **`proyecto_sicd.qgs`**: Proyecto QGIS preconfigurado para cargar las capas de denuncias.

## Instalación

### Requisitos

- QGIS 2.14.14 Essen
- Python 2.7 (incluido con QGIS 2.14)
- PyQt4 (incluido con QGIS 2.14)

### Configuración

1. **Abrir QGIS 2.14.14**

2. **Configurar la ruta del archivo GeoJSON**

   Editar el archivo `auto_refresh_sicd.py` y modificar la variable `RUTA_GEOJSON`:

   ```python
   RUTA_GEOJSON = r"C:\Users\Usuario\OneDrive\Desktop\SICD\data\OUTPUT\QGIS_SYNC\denuncias_activas.geojson"
   ```

3. **Cargar el script en QGIS**

   - Ir a `Complementos > Consola de Python`
   - Copiar y pegar el contenido completo de `auto_refresh_sicd.py`
   - Presionar Enter

4. **Verificar funcionamiento**

   Deberías ver en la consola:

   ```
   ============================================================
   SICD Monitor para QGIS 2.14.14
   ============================================================
   Archivo monitoreado: C:\...\denuncias_activas.geojson
   Intervalo de actualizacion: 5000 ms
   ============================================================
   [SICD] Monitoreo iniciado. Verificando cada 5 segundos.
   ```

## Uso

### Comandos disponibles en la consola de Python

```python
# Detener monitoreo
monitor_sicd.detener()

# Reiniciar monitoreo
monitor_sicd.iniciar()

# Forzar actualización inmediata
monitor_sicd.forzar_actualizacion()

# Zoom al extent de las denuncias
monitor_sicd.zoom_a_denuncias()
```

### Flujo de trabajo

1. **Iniciar SICD** (aplicación Streamlit)
2. **Iniciar QGIS** y ejecutar el script
3. **Procesar denuncias** en SICD
4. Los puntos aparecerán automáticamente en QGIS (cada 5 segundos)

### Archivar denuncias

Desde SICD:

1. Ir al panel lateral "Sincronización QGIS"
2. Click en "📦 Archivar en histórico"
3. Las denuncias se moverán a la carpeta `historico/`

## Colores por tipo de delito

| Tipo de delito       | Color                |
| -------------------- | -------------------- |
| HURTO                | 🔵 Azul (#0000FF)    |
| ROBO                 | 🔴 Rojo (#FF0000)    |
| ESTAFA               | 🟠 Naranja (#FFA500) |
| PORTACION_ARMA_FUEGO | ⚫ Negro (#000000)   |

## Estructura de archivos

```
data/OUTPUT/QGIS_SYNC/
├── denuncias_activas.geojson    # Archivo principal (actualización en tiempo real)
└── historico/
    ├── denuncias_20250115_120000.geojson
    ├── denuncias_20250116_180000.geojson
    └── ...
```

## Troubleshooting

### El archivo GeoJSON no se actualiza

1. Verificar que SICD está corriendo
2. Verificar que las denuncias procesadas tienen coordenadas
3. Revisar los logs en `logs/sicd.log`

### La capa no se actualiza en QGIS

1. Verificar que el script está ejecutándose (ver mensajes en consola)
2. Usar `monitor_sicd.forzar_actualizacion()` para actualizar manualmente
3. Verificar la ruta del archivo en el script

### Error "Archivo no encontrado"

El script esperará automáticamente a que SICD genere el archivo. Una vez que se procese la primera denuncia, la capa aparecerá.

## Notas técnicas

- El archivo GeoJSON usa el sistema de coordenadas CRS84 (EPSG:4326)
- Las coordenadas están en formato [longitud, latitud] (estándar GeoJSON)
- El script verifica cambios cada 5 segundos (configurable)
- La escritura del archivo es atómica (primero escribe .tmp, luego renombra)
