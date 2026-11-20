# One-click setup: installs what is missing, builds YTDownloader.exe, opens the documentation.
# Normally started by double-clicking setup.bat.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$is32BitWindows = ($env:PROCESSOR_ARCHITECTURE -eq "x86") -and -not $env:PROCESSOR_ARCHITEW6432
$arch = if ($is32BitWindows) { "x86" } else { "x64" }
$bits = if ($is32BitWindows) { 32 } else { 64 }
$distDir = if ($arch -eq "x86") { "dist-x86" } else { "dist" }

function Write-Step([string]$text) { Write-Host ""; Write-Host "==> $text" -ForegroundColor Cyan }
function Write-Ok([string]$text) { Write-Host "    OK  $text" -ForegroundColor Green }
function Write-Info([string]$text) { Write-Host "    $text" }

function Update-PathFromRegistry {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Test-Command([string]$name) { [bool](Get-Command $name -ErrorAction SilentlyContinue) }

function Install-WithWinget([string]$id, [string]$label, [string[]]$extra = @()) {
    if (-not (Test-Command "winget")) {
        throw "winget is not available, so $label cannot be installed automatically. " +
              "Install 'App Installer' from the Microsoft Store, or install $label yourself, then run setup again."
    }
    Write-Info "Installing $label with winget (this can take a few minutes)..."
    & winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements @extra
    # winget returns a non-zero code when the package is already installed; check the result instead.
    Update-PathFromRegistry
}

function Find-PythonExe {
    $candidates = @()
    $candidates += , @("python")
    if (Test-Command "py") {
        $tag = if ($bits -eq 32) { "-32" } else { "-64" }
        foreach ($v in "3.13", "3.12", "3.11", "3.10", "3.14", "3.15") { $candidates += , @("py", "-$v$tag") }
    }
    foreach ($v in "313", "312", "311", "310", "314", "315") {
        $p = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$v\python.exe"
        if (Test-Path $p) { $candidates += , @($p) }
    }
    $check = "import struct,sys; print(sys.executable if sys.version_info >= (3,10) and struct.calcsize('P')*8 == $bits else '')"
    foreach ($c in $candidates) {
        $exe = $c[0]; $pre = @($c | Select-Object -Skip 1)
        try {
            $out = (& $exe @pre -c $check 2>$null | Select-Object -Last 1)
            if ($out -and (Test-Path $out.Trim())) { return $out.Trim() }
        } catch { }
    }
    return $null
}

try {
    Write-Host "YTDownloader setup ($arch)" -ForegroundColor White
    Write-Host "This installs what is missing, builds YTDownloader.exe and opens the documentation."

    # 1. Python ---------------------------------------------------------------
    Write-Step "Checking Python 3.10+ ($bits-bit)"
    $python = Find-PythonExe
    if (-not $python) {
        $pyArgs = @("--scope", "user", "--override", "/quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1")
        if ($is32BitWindows) { $pyArgs += @("--architecture", "x86") }
        Install-WithWinget "Python.Python.3.12" "Python 3.12" $pyArgs
        $python = Find-PythonExe
        if (-not $python) { throw "Python was not found after installing. Close this window and run setup.bat again." }
    }
    Write-Ok "Python: $python"

    # 2. ffmpeg ---------------------------------------------------------------
    Write-Step "Checking ffmpeg"
    if (-not (Test-Command "ffmpeg")) {
        Install-WithWinget "Gyan.FFmpeg" "ffmpeg"
        if (-not (Test-Command "ffmpeg")) {
            Write-Host "    ffmpeg was installed but this window cannot see it yet. It will work in a new CMD window." -ForegroundColor Yellow
        }
    }
    if (Test-Command "ffmpeg") { Write-Ok "ffmpeg: $((Get-Command ffmpeg).Source)" }

    # 3. JavaScript runtime (needed by YouTube) --------------------------------
    Write-Step "Checking Deno / Node.js (YouTube needs one of them)"
    if (-not ((Test-Command "deno") -or (Test-Command "node"))) {
        if ($is32BitWindows) {
            Write-Host "    Deno and recent Node.js do not run on 32-bit Windows. YouTube downloads may fail." -ForegroundColor Yellow
        } else {
            Install-WithWinget "DenoLand.Deno" "Deno"
        }
    }
    if (Test-Command "deno") { Write-Ok "Deno: $((Get-Command deno).Source)" }
    elseif (Test-Command "node") { Write-Ok "Node.js: $((Get-Command node).Source)" }

    # 4. Build ----------------------------------------------------------------
    Write-Step "Building YTDownloader.exe (installs Python packages first)"
    & "$PSScriptRoot\build.ps1" -Arch $arch -Python $python
    $exe = Join-Path $PSScriptRoot "$distDir\YTDownloader.exe"
    if (-not (Test-Path $exe)) { throw "The build finished but $exe was not created." }
    Write-Ok "Built: $exe"

    # 5. Documentation + output folder -----------------------------------------
    Write-Step "Opening the documentation and the output folder"
    Start-Process (Join-Path $PSScriptRoot "docs\index.html")
    Start-Process explorer.exe -ArgumentList "`"$(Join-Path $PSScriptRoot $distDir)`""

    Write-Host ""
    Write-Host "All done!" -ForegroundColor Green
    Write-Host "Your program is in: $(Join-Path $PSScriptRoot $distDir)"
    Write-Host "Open CMD in that folder and run:   ytd -url    or    ytd -ui"
    exit 0
}
catch {
    Write-Host ""
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "See the Troubleshooting section in docs\index.html or README.md."
    exit 1
}
