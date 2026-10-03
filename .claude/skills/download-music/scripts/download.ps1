# Downloads one or more links by running the repo's downloader.py.
# downloader.py only reads links.txt, so this temporarily swaps in the given links and
# restores the user's original links.txt byte-for-byte afterwards.
#
# Usage: download.ps1 -Url <link>[,<link>...] [-Folder <path>] [-Format mp3|webm]
# mp3 is the default because Roll20 only accepts mp3; webm is the repo's original Foundry VTT format.
# Ends with a summary block (RESULT / NEW FILE / ALREADY HAD / ERROR lines).
# Exit code: 0 = every link produced a file, 1 = at least one failed, 2 = couldn't start.

param(
    [Parameter(Mandatory = $true)][string[]]$Url,
    [string]$Folder = (Join-Path $env:USERPROFILE 'Downloads\YouTube-Music'),
    [ValidateSet('mp3', 'webm')][string]$Format = 'mp3'
)

. (Join-Path $PSScriptRoot 'common.ps1')
$ErrorActionPreference = 'Continue'

$py = Find-Python
if (-not $py) {
    Write-Output "ERROR: Python not found. Run preflight.ps1 for the fix."
    exit 2
}

$Url = $Url | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ }
foreach ($u in $Url) {
    if ($u -notmatch '^https?://') {
        Write-Output "ERROR: '$u' is not a link (it should start with https://)."
        exit 2
    }
}

New-Item -ItemType Directory -Force -Path $Folder | Out-Null
$Folder = (Resolve-Path $Folder).Path
$before = @(Get-ChildItem -LiteralPath $Folder -File | ForEach-Object { $_.Name })

$linksFile = Join-Path $RepoRoot 'links.txt'
$hadLinks = Test-Path $linksFile
if ($hadLinks) { $original = [IO.File]::ReadAllBytes($linksFile) }

$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$log = @()
try {
    [IO.File]::WriteAllText($linksFile, ($Url -join "`n") + "`n")
    Push-Location $RepoRoot
    & $py downloader.py --generate $Folder --format $Format 2>&1 | ForEach-Object {
        $line = "$_"
        $log += $line
        Write-Output $line
    }
} finally {
    Pop-Location
    if ($hadLinks) { [IO.File]::WriteAllBytes($linksFile, $original) } else { Remove-Item $linksFile -ErrorAction SilentlyContinue }
}

$new = @(Get-ChildItem -LiteralPath $Folder -File |
         Where-Object { $before -notcontains $_.Name -and $_.Name -ne 'playlist.json' -and $_.Extension -notin '.part', '.ytdl' })
# Only count the target format: for mp3, yt-dlp also reports reusing an existing .webm as its conversion source.
$already = @($log | Where-Object { $_ -match "\.$Format has already been downloaded" })
$errors = @($log | Where-Object { $_ -match '^ERROR:|^Error:|Error during download' })

Write-Output ''
Write-Output '===== SUMMARY ====='
Write-Output "RESULT: $($new.Count) new file(s), $($already.Count) already downloaded, $($errors.Count) error line(s). Folder: $Folder"
foreach ($f in $new) { Write-Output ("NEW FILE: {0} ({1:N1} MB)" -f $f.Name, ($f.Length / 1MB)) }
foreach ($a in $already) { Write-Output "ALREADY HAD: $a" }
foreach ($e in $errors) { Write-Output "ERROR: $e" }
if ($new | Where-Object { $_.Extension -ne ".$Format" }) {
    Write-Output "NOTE: some files aren't .$Format, so they aren't listed in playlist.json."
}

if ($errors.Count -gt 0 -or ($new.Count + $already.Count) -lt $Url.Count) { exit 1 }
exit 0
