param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create .venv with uv sync --locked --extra transcribe --extra build first.' }
$version = (& $python -c 'from local_caption import __version__; print(__version__)').Trim()
$distRoot = Join-Path (Get-Location) "dist\v$version"
$appDir = Join-Path $distRoot 'LocalCaption'
$running = @(Get-Process -Name LocalCaption,LocalCaptionWorker -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($appDir + '\', [StringComparison]::OrdinalIgnoreCase) })
if ($running.Count -gt 0) { throw "Close the running app/worker in $appDir before rebuilding this version. No build files changed." }
if (-not $SkipTests) {
    & $python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
}
& $python -m PyInstaller --noconfirm --clean --distpath $distRoot packaging/local-caption.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
Copy-Item README.md, SECURITY.md, VALIDATION.md -Destination $appDir
Write-Host "Built $appDir\LocalCaption.exe. Distribute the ENTIRE LocalCaption folder."
Write-Host 'Models and FFmpeg/FFprobe remain external. See README.md.'
