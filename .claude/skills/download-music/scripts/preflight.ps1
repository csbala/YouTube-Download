# Checks everything downloader.py needs before a download. Python is checked here; the rest comes
# from `downloader.py doctor`, so the tool lookups live in one place.
# One line per check: [OK], [WARN] (works but risky) or [MISSING] (blocks the download), each with a fix.
# Last line is PYTHON=<path> when a usable Python was found.
# Exit code: 0 = ready, 1 = something blocking is missing.

. (Join-Path $PSScriptRoot 'common.ps1')

$blocking = 0

# Python
$py = Find-Python
if ($py) {
    $pyVersion = (& $py --version 2>&1 | Out-String).Trim()
    Write-Output "[OK] Python: $pyVersion at $py"
} else {
    Write-Output "[MISSING] Python 3 is not installed (only the Windows Store stub was found). Fix: winget install -e --id Python.Python.3.12"
    $blocking++
}

# The repo's script itself, which checks yt-dlp, Node.js, ffmpeg and cookies.txt
if (-not (Test-Path (Join-Path $RepoRoot 'downloader.py'))) {
    Write-Output "[MISSING] downloader.py not found in $RepoRoot"
    $blocking++
} elseif ($py) {
    Write-Output "[OK] downloader.py at $RepoRoot"
    $env:PYTHONIOENCODING = 'utf-8'
    Push-Location $RepoRoot
    try { & $py downloader.py doctor } finally { Pop-Location }
    if ($LASTEXITCODE -ne 0) { $blocking++ }
}

if ($py) { Write-Output "PYTHON=$py" }
exit ([int]($blocking -gt 0))
