# Checks everything downloader.py needs before a download.
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

# yt-dlp
if ($py) {
    $yt = Get-YtDlpVersion $py
    if (-not $yt) {
        Write-Output "[MISSING] yt-dlp is not installed for this Python. Fix: `"$py`" -m pip install -U yt-dlp"
        $blocking++
    } elseif ($yt -lt $MinYtDlpVersion) {
        Write-Output "[MISSING] yt-dlp $yt is too old (downloader.py needs $MinYtDlpVersion or newer). Fix: `"$py`" -m pip install -U yt-dlp"
        $blocking++
    } else {
        Write-Output "[OK] yt-dlp $yt"
    }
}

# Node.js, at the exact path downloader.py hardcodes
$node = 'C:\Program Files\nodejs\node.exe'
if (Test-Path $node) {
    Write-Output "[OK] Node.js: $((& $node --version 2>$null) -join '') at $node"
} else {
    Write-Output "[MISSING] Node.js not found at $node (downloader.py uses it to solve YouTube's JS challenge). Fix: winget install -e --id OpenJS.NodeJS.LTS"
    $blocking++
}

# ffmpeg, needed for mp3 (the default format, because Roll20 only accepts mp3)
$ffmpeg = Find-FFmpeg
if ($ffmpeg) {
    Write-Output "[OK] ffmpeg at $ffmpeg"
} else {
    Write-Output "[MISSING] ffmpeg not found (needed for mp3; webm still works without it). Fix: winget install -e --id Gyan.FFmpeg"
    $blocking++
}

# Cookies. Never print the contents: they are the user's YouTube login.
$cookies = Join-Path $RepoRoot 'cookies.txt'
if (-not (Test-Path $cookies)) {
    Write-Output "[WARN] cookies.txt not found in the repo. Public videos usually work; age-restricted ones and 'confirm you're not a bot' blocks will fail. Fix: export YouTube cookies with the 'Get cookies.txt LOCALLY' browser extension and save them as cookies.txt in the repo."
} else {
    $header = Get-Content $cookies -TotalCount 1
    $ageDays = [int]((Get-Date) - (Get-Item $cookies).LastWriteTime).TotalDays
    if ($header -notmatch 'HTTP Cookie File') {
        Write-Output "[WARN] cookies.txt isn't in Netscape format (first line should mention 'HTTP Cookie File'). Re-export it with 'Get cookies.txt LOCALLY'."
    } elseif ($ageDays -gt 30) {
        Write-Output "[WARN] cookies.txt is $ageDays days old and may have expired. Re-export it if downloads fail with a sign-in or bot error."
    } else {
        Write-Output "[OK] cookies.txt ($ageDays days old)"
    }
}

# The repo's script itself
if (Test-Path (Join-Path $RepoRoot 'downloader.py')) {
    Write-Output "[OK] downloader.py at $RepoRoot"
} else {
    Write-Output "[MISSING] downloader.py not found in $RepoRoot"
    $blocking++
}

if ($py) { Write-Output "PYTHON=$py" }
exit ([int]($blocking -gt 0))
