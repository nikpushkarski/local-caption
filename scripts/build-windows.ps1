param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv with uv sync --locked --extra transcribe --extra build first.' }
if (-not $SkipTests) {
    & $python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
}
& $python -m PyInstaller --noconfirm --clean packaging/local-caption.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
Copy-Item README.md, SECURITY.md, VALIDATION.md -Destination dist/LocalCaption
Write-Host 'Built dist\LocalCaption\LocalCaption.exe. Distribute the ENTIRE LocalCaption folder.'
Write-Host 'Models and FFmpeg/FFprobe remain external. See README.md.'
