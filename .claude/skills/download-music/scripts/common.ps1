# Shared helpers for the download-music skill. Dot-source this file.

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path

# yt-dlp release that added --js-runtimes / --remote-components, which downloader.py uses.
$MinYtDlpVersion = '2025.11.12'

function Find-Python {
    # Returns the full path of a working python.exe, or $null.
    # Skips the Windows Store "python" stub, which prints "Python was not found" and exits 49.
    $candidates = @()
    foreach ($name in @('python', 'py', 'python3')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += $cmd.Source }
    }
    # A fresh winget install isn't on this session's PATH yet, so also look where installers put it.
    $candidates += Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
                                 "C:\Program Files\Python3*\python.exe",
                                 "C:\Python3*\python.exe" -ErrorAction SilentlyContinue |
                   Sort-Object FullName -Descending | ForEach-Object { $_.FullName }

    foreach ($exe in $candidates) {
        $real = & $exe -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $real) { return ($real | Select-Object -First 1).Trim() }
    }
    return $null
}

function Find-FFmpeg {
    # Same lookup as downloader.py's find_ffmpeg(): PATH first, then winget's package folder.
    $cmd = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $hit = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe" -ErrorAction SilentlyContinue |
           Select-Object -First 1
    if ($hit) { return $hit.FullName }
    return $null
}

function Get-YtDlpVersion([string]$Python) {
    $v = & $Python -m yt_dlp --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $v) { return ($v | Select-Object -First 1).Trim() }
    return $null
}
