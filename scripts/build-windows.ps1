param([switch]$SkipTests, [ValidateSet('cuda', 'cpu')][string]$Variant = 'cuda')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$environment = if ($Variant -eq 'cpu') { '.venv-cpu' } else { '.venv' }
$python = Join-Path (Get-Location) "$environment\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Create $environment with uv sync --locked --extra build --extra $(if ($Variant -eq 'cpu') { 'transcribe' } else { 'cuda' }) first." }
$cudaRuntime = (& $python -c 'import torch; print(bool(torch.version.cuda))').Trim()
if (($Variant -eq 'cpu' -and $cudaRuntime -ne 'False') -or ($Variant -eq 'cuda' -and $cudaRuntime -ne 'True')) {
    throw "Wrong PyTorch runtime in $environment. Refusing to mislabel the $Variant release."
}
$version = (& $python -c 'from local_caption import __version__; print(__version__)').Trim()
$folder = if ($Variant -eq 'cpu') { "v$version-cpu" } else { "v$version" }
$distRoot = Join-Path (Get-Location) "dist\$folder"
$appDir = Join-Path $distRoot 'LocalCaption'
$running = @(Get-Process -Name LocalCaption,LocalCaptionWorker -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($appDir + '\', [StringComparison]::OrdinalIgnoreCase) })
if ($running.Count -gt 0) { throw "Close the running app/worker in $appDir before rebuilding this version. No build files changed." }
if (-not $SkipTests) {
    & $python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
}
$workRoot = Join-Path (Get-Location) "build\$folder"
& $python -m PyInstaller --noconfirm --clean --workpath $workRoot --distpath $distRoot packaging/local-caption.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
Copy-Item README.md, SECURITY.md, VALIDATION.md, LICENSE, THIRD_PARTY_NOTICES.md, CUDA_REDISTRIBUTION.md -Destination $appDir
Copy-Item licenses -Destination $appDir -Recurse -Force
& $python scripts/collect-notices.py $appDir $Variant
if ($LASTEXITCODE -ne 0) { throw 'Dependency license audit failed; do not distribute this build.' }
Write-Host "Built $appDir\LocalCaption.exe. Distribute the ENTIRE LocalCaption folder."
Write-Host 'Models and FFmpeg/FFprobe remain external. See README.md.'
