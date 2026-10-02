param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\', '/')
$gitRoot = (& git -C $root rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or -not $gitRoot -or
    [IO.Path]::GetFullPath($gitRoot).TrimEnd('\', '/') -ine $root) {
    throw 'This script must be run from its own Git repository. Nothing was deleted.'
}

# Git determines what is safe to remove: .git and tracked source are never targets.
$preview = @(& git -C $root clean -ndx)
if ($LASTEXITCODE -ne 0) { throw 'Could not preview git clean. Nothing was deleted.' }
if (-not $preview.Count) { Write-Host 'Already clean; nothing to remove.'; exit 0 }
Write-Host 'Untracked and ignored files/directories that would be deleted:'
$preview | ForEach-Object { Write-Host $_ }
Write-Warning 'This includes ALL local builds, virtual environments, caches, models/media or personal files kept inside the repository. Move anything you need OUTSIDE this folder first.'
if (-not $Apply) {
    Write-Host 'Preview only. Run with -Apply to request deletion.'
    exit 0
}

$changes = @(& git -C $root status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0) { throw 'Could not check tracked changes. Nothing was deleted.' }
if ($changes.Count) { throw 'Tracked files have changes. Commit/stash/revert them first; nothing was deleted.' }

# Refuse to partially clean a live build; never close another process for the user.
$running = @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
    $_.ExecutablePath -and $_.ExecutablePath.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)
})
if ($running.Count) {
    $ids = ($running.ProcessId -join ', ')
    throw "A process is running from this repository (PID: $ids). Close it yourself and retry; nothing was deleted."
}
$answer = Read-Host 'Type DELETE to permanently remove everything listed above'
if ($answer -cne 'DELETE') { Write-Host 'Cancelled; nothing was deleted.'; exit 0 }
$now = @(& git -C $root clean -ndx)
if ($LASTEXITCODE -ne 0 -or (Compare-Object $preview $now)) {
    throw 'The cleanup list changed or could not be checked. Review the new preview and retry; nothing was deleted.'
}
& git -C $root clean -fdx
if ($LASTEXITCODE -ne 0) { throw 'Git clean reported an error; inspect the folder before retrying.' }
Write-Host 'Cleanup finished. Git history and tracked project files were preserved.'
