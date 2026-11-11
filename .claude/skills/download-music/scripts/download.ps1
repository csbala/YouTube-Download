# Downloads one or more links by running the repo's downloader.py.
#
# Usage: download.ps1 -Url <link>[,<link>...] [-Folder <path>] [-Format mp3|m4a|webm]
# mp3 is the default (it plays everywhere, and Roll20 only accepts mp3); m4a is YouTube's AAC audio with no
# quality loss; webm is YouTube's original audio and needs no ffmpeg.
# Ends with a summary block (RESULT / NEW FILE / ALREADY HAD / FAILED / NOT FINISHED / ERROR lines).
# Exit code: downloader.py's (0 = every link downloaded, 1 = at least one failed, 2 = couldn't start, 130 = Ctrl+C).
#
# downloader.py runs with --json, so the results come from its JSON lines on stdout, not from matching
# yt-dlp's wording. yt-dlp's own ERROR/WARNING lines arrive on stderr and are passed through as-is.

param(
    [Parameter(Mandatory = $true)][string[]]$Url,
    [string]$Folder = (Join-Path $env:USERPROFILE 'Downloads\YouTube-Music'),
    [ValidateSet('mp3', 'm4a', 'webm')][string]$Format = 'mp3'
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
$before = @(Get-ChildItem -LiteralPath $Folder -File | ForEach-Object { $_.FullName })

$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$summary = $null
$errors = @()
$code = 2
try {
    Push-Location $RepoRoot
    & $py downloader.py download $Folder @Url --format $Format --json 2>&1 | ForEach-Object {
        $line = "$_"
        $record = $null
        if ($line.StartsWith('{')) {
            try { $record = $line | ConvertFrom-Json } catch { $record = $null }
        }
        if (-not $record) {
            Write-Output $line  # yt-dlp's own stderr output
            return
        }
        switch ($record.event) {
            'batch_started'   { Write-Output "Downloading $($record.link_count) link(s) to $($record.folder) as .$($record.audio_format)..." }
            'link_started'    { Write-Output "Downloading: $($record.link)" }
            'link_done'       { Write-Output "Done: $($record.link)" }
            'link_errored'    { $errors += "$($record.link): $($record.reason)" }
            'title_clash'     { $errors += "$($record.title) has the same file name as an earlier video (retry it alone with --suffix)" }
            'run_failed'      { $errors += $record.message }
            'node_missing'    { Write-Output "WARNING: Node.js not found; YouTube downloads may fail." }
            'cookies_missing' { Write-Output "WARNING: no cookies.txt; age-restricted videos may fail." }
            'batch_finished'  { $summary = $record }
        }
    }
    $code = $LASTEXITCODE
} finally {
    Pop-Location
}

Write-Output ''
Write-Output '===== SUMMARY ====='
if ($summary) {
    $files = @($summary.files | Where-Object { $_ })
    $new = @($files | Where-Object { $before -notcontains $_ })
    $already = @($files | Where-Object { $before -contains $_ })
    Write-Output "RESULT: $($summary.downloaded_count) of $($summary.link_count) link(s) downloaded, $($new.Count) new file(s), $($already.Count) already downloaded. Folder: $Folder"
    foreach ($f in $new) {
        $size = if (Test-Path -LiteralPath $f) { (Get-Item -LiteralPath $f).Length / 1MB } else { 0 }
        Write-Output ("NEW FILE: {0} ({1:N1} MB)" -f (Split-Path $f -Leaf), $size)
    }
    foreach ($f in $already) { Write-Output "ALREADY HAD: $(Split-Path $f -Leaf)" }
    foreach ($l in @($summary.failed_links | Where-Object { $_ })) { Write-Output "FAILED: $l" }
    foreach ($l in @($summary.unfinished | Where-Object { $_ })) { Write-Output "NOT FINISHED: $l" }
} else {
    Write-Output "RESULT: the download didn't run. Folder: $Folder"
}
foreach ($e in $errors) { Write-Output "ERROR: $e" }

# downloader.py's own exit code: 0 = all links downloaded, 1 = some failed, 2 = couldn't start, 130 = Ctrl+C
exit $code
