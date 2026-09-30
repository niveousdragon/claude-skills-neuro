# Sets up everything meeting-memo needs on a clean Windows machine:
# Python, pandoc, faster-whisper and the speech model. Safe to run again: what is
# already installed is skipped. Output is ASCII only (cp1251 consoles).
#
# Run:  powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

function Refresh-Path {
    # winget installs update PATH in the registry only; this session would not see them.
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Have($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Winget-Install($id) {
    if (-not (Have "winget")) {
        Write-Host "[FAILED] winget not found. Install $id by hand, then run this script again."
        exit 1
    }
    winget install -e --id $id --accept-source-agreements --accept-package-agreements --silent
    Refresh-Path
}

# 1. Python. The Microsoft Store stub named python.exe prints a hint and exits, so
#    "python is on PATH" is not enough: ask it for its version.
$py = $null
foreach ($c in @("python", "py")) {
    if (Have $c) {
        $v = & $c --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -match "Python 3\.(\d+)" -and [int]$Matches[1] -ge 9) { $py = $c; break }
    }
}
if (-not $py) {
    Write-Host "[..] installing Python 3.12"
    Winget-Install "Python.Python.3.12"
    $py = "python"
}
Write-Host "[OK] $(& $py --version)"

# 2. pandoc, for the reader-friendly .docx.
if (-not (Have "pandoc")) {
    Write-Host "[..] installing pandoc"
    Winget-Install "JohnMacFarlane.Pandoc"
}
if (-not (Have "pandoc")) { Write-Host "[FAILED] pandoc still not on PATH; open a new terminal and rerun"; exit 1 }
Write-Host "[OK] $((pandoc --version | Select-Object -First 1))"

# 3. faster-whisper. It reads .webm/.mp4/.m4a itself, no ffmpeg needed.
Write-Host "[..] installing faster-whisper"
& $py -m pip install --user --upgrade --quiet faster-whisper
if ($LASTEXITCODE -ne 0) { Write-Host "[FAILED] pip install faster-whisper"; exit 1 }
Write-Host "[OK] faster-whisper installed"

# 4. The model (~1.6 GB, once) and a run on silence to prove the whole chain works.
#    If huggingface.co is unreachable, set HF_ENDPOINT to a mirror and rerun.
Write-Host "[..] downloading the speech model on first run (about 1.6 GB), then a self-test"
& $py (Join-Path $here "transcribe.py") --check
if ($LASTEXITCODE -ne 0) { Write-Host "[FAILED] model self-test"; exit 1 }

Write-Host "[OK] meeting-memo is ready"
