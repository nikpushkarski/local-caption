param([switch]$WhatIf)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
# Only obsolete, reproducible local build copies. Never touch the current CPU app.
foreach ($version in @('v0.3.0', 'v0.4.0')) {
    $folder = Join-Path $root "dist\$version"
    if (-not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
    $running = @(Get-Process -Name LocalCaption,LocalCaptionWorker -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith($folder + '\', [StringComparison]::OrdinalIgnoreCase) })
    if ($running.Count) {
        Write-Warning "Keeping $folder: app/worker still running (PID: $(($running.Id -join ', '))). Close it yourself and rerun."
        continue
    }
    if ($WhatIf) { Write-Host "Would remove: $folder"; continue }
    Remove-Item -LiteralPath $folder -Recurse -Force
    Write-Host "Removed: $folder"
}
