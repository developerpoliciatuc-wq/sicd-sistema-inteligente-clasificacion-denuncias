# Instala dependencias externas en Windows: Tesseract OCR + Poppler
# Requiere ejecutar PowerShell como Administrador para PATH del sistema.

$ErrorActionPreference = 'Stop'

Write-Host 'Instalando Tesseract (winget)…'
winget install -e --id UB-Mannheim.TesseractOCR

# Intentar instalar idioma español (según instalador UB Mannheim, suele incluirse; si no, se puede descargar luego)

Write-Host 'Instalando Poppler (descarga y extracción en ./tools/poppler)…'

# URL válida (release latest)
$popplerUrl = 'https://github.com/oschwartz10612/poppler-windows/releases/download/v25.12.0-0/Release-25.12.0-0.zip'

$tmpZip = Join-Path $env:TEMP 'poppler.zip'
$tmpDir = Join-Path $env:TEMP 'poppler_extracted'

Invoke-WebRequest -Uri $popplerUrl -OutFile $tmpZip
if (Test-Path $tmpDir) { Remove-Item -Recurse -Force $tmpDir }
Expand-Archive -Path $tmpZip -DestinationPath $tmpDir

# Destino local (no requiere Admin)
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$dest = Join-Path $repoRoot 'tools\poppler'

if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Path $dest | Out-Null

# El zip trae una carpeta Release-xx… copiamos su contenido
$inner = Get-ChildItem $tmpDir | Select-Object -First 1
Copy-Item -Recurse -Force (Join-Path $inner.FullName '*') $dest

$bin = Join-Path $dest 'Library\bin'
if (Test-Path $bin) {
  Write-Host "Poppler instalado en: $dest"
  Write-Host "Configura POPPLER_PATH en tu .env con: $bin"
} else {
  Write-Host "Poppler instalado en: $dest (no se encontró Library\\bin; revisa la estructura)"
}

Write-Host 'Listo.'
