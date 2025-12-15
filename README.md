# SCID — Sistema de Clasificación Inteligente de Denuncias

Web App (Streamlit) para cargar denuncias (PDF/Imagen), extraer texto (PDF nativo u OCR), clasificar con Gemini API y archivar en la estructura del servidor.

## Requisitos

- Windows
- Python 3.11
- Acceso al recurso compartido `\\ANALISIS-3` (si se usa en producción)

## Instalación (Windows)

1. Dependencias externas (OCR/PDF)

- Abrí PowerShell **como Administrador** y ejecutá:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows_deps.ps1
```

2. Entorno virtual + dependencias Python (en tu terminal bash)

```bash
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

3. Configuración

- Copiá `.env.example` a `.env` y completá al menos:
  - `GEMINI_API_KEY`
  - (opcional) `TESSERACT_CMD` y `POPPLER_PATH` si no quedaron en PATH

## Ejecutar

```bash
source venv/Scripts/activate
streamlit run src/app.py
```

## Notas

- Si falta `GEMINI_API_KEY`, el sistema procesa OCR/extracción pero envía a revisión (no clasifica).
- La carpeta de revisión manual se controla con `REVISION_ROOT` (por defecto `\\ANALISIS-3\Analisis-3\MAPA DEL DELITO\_REVISION_MANUAL`).
- El diccionario maestro está en `config/comisarias.json`.
- Para pruebas locales sin acceso a `\\ANALISIS-3`, definí en `.env`:
  - `DEST_ROOT=./data/OUTPUT`
  - `REVISION_ROOT=./data/_REVISION_MANUAL`

# sicd-sistema-inteligente-clasificacion-denuncias
