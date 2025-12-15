# Fixtures de testing

Este directorio se usa para datos de prueba.

En este repo, los PDFs de integración se generan **en runtime** dentro de los tests (para evitar subir binarios).

## Ejecutar integración (OCR/PDF)

Requiere Tesseract y Poppler instalados.

- `RUN_INTEGRATION=1`
- (opcional) `TESSERACT_CMD` apuntando a `tesseract.exe`
- (opcional) `POPPLER_PATH` apuntando a la carpeta `bin` de Poppler
- (opcional) `TESSERACT_LANG` (default `eng`; podés usar `spa` si tenés instalado el idioma)

Ejemplo (bash en Windows):

```bash
export RUN_INTEGRATION=1
# export TESSERACT_CMD="C:/Program Files/Tesseract-OCR/tesseract.exe"
# export POPPLER_PATH="C:/.../poppler/Library/bin"
python -m pytest -m integration
```
