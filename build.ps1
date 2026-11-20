# Builds YTDownloader.exe with PyInstaller.
#
#   powershell -ExecutionPolicy Bypass -File build.ps1              64-bit -> dist\YTDownloader.exe
#   powershell -ExecutionPolicy Bypass -File build.ps1 -Arch x86    32-bit -> dist-x86\YTDownloader.exe
#   ... -Python C:\path\to\python.exe                               use a specific Python
#
# The 32-bit build needs a 32-bit Python 3.10+ (python.org "Windows installer (32-bit)",
# or:  uv python install cpython-3.12-windows-x86-none).
param(
    [ValidateSet("x64", "x86")]
    [string]$Arch = "x64",
    [string]$Python
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$bits = if ($Arch -eq "x86") { 32 } else { 64 }
$suffix = if ($Arch -eq "x86") { "-x86" } else { "" }
$venv = ".venv$suffix"
$dist = "dist$suffix"
$work = "build$suffix"

function Get-Bits([string]$exe, [string[]]$pre = @()) {
    try {
        $out = & $exe @pre -c "import struct,sys; print(struct.calcsize('P')*8 if sys.version_info >= (3,10) else 0)" 2>$null
        return [int]($out | Select-Object -Last 1)
    } catch { return 0 }
}

function Find-Python {
    if ($Python) {
        if ((Get-Bits $Python) -ne $bits) { throw "$Python is not a $bits-bit Python 3.10+." }
        return @($Python)
    }
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $tag = if ($bits -eq 32) { "-32" } else { "-64" }
        foreach ($v in "3.13", "3.12", "3.11", "3.10", "3.15", "3.14") { $candidates += , @("py", "-$v$tag") }
    }
    if ($bits -eq 64) { $candidates = , @("python") + $candidates }
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $uvArch = if ($bits -eq 32) { "x86" } else { "x86_64" }
        $found = & uv python find "cpython-3.12-windows-$uvArch-none" 2>$null
        if ($LASTEXITCODE -eq 0 -and $found) { $candidates += , @($found.Trim()) }
    }
    foreach ($c in $candidates) {
        $exe = $c[0]; $pre = @($c | Select-Object -Skip 1)
        if ((Get-Bits $exe $pre) -eq $bits) { return $c }
    }
    throw "No $bits-bit Python 3.10+ found. Install one, or pass -Python <path to python.exe>."
}

if (-not (Test-Path "$venv\Scripts\python.exe")) {
    $base = @(Find-Python)  # @() keeps a one-item result as an array
    Write-Host "Creating $venv with: $($base -join ' ')"
    $exe = $base[0]; $pre = @($base | Select-Object -Skip 1)
    & $exe @pre -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create $venv" }
}
$py = "$venv\Scripts\python.exe"
if ((Get-Bits $py) -ne $bits) { throw "$venv is not $bits-bit. Delete the $venv folder and run again." }

Write-Host "Installing dependencies ($Arch)..."
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "Building YTDownloader.exe ($Arch)..."
& $py -m PyInstaller --noconfirm --clean --onefile --console `
    --name YTDownloader `
    --distpath $dist --workpath $work --specpath $work `
    --add-data "$PSScriptRoot\ytd\web;ytd\web" `
    --collect-all yt_dlp_ejs `
    --hidden-import tkinter `
    run_ytd.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Copy-Item ytd.cmd "$dist\ytd.cmd" -Force
Write-Host ""
Write-Host "Done ($Arch):" -ForegroundColor Green
Get-ChildItem $dist -File | Format-Table Name, @{n = "Size (MB)"; e = { "{0:N1}" -f ($_.Length / 1MB) } }
