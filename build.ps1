# Builds dist\YTDownloader.exe and dist\ytd.cmd
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}
$py = ".venv\Scripts\python.exe"

Write-Host "Installing dependencies..."
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

Write-Host "Building YTDownloader.exe..."
& $py -m PyInstaller --noconfirm --clean --onefile --console `
    --name YTDownloader `
    --add-data "ytd\web;ytd\web" `
    --collect-all yt_dlp_ejs `
    --hidden-import tkinter `
    run_ytd.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Copy-Item ytd.cmd dist\ytd.cmd -Force
Write-Host ""
Write-Host "Done:" -ForegroundColor Green
Get-ChildItem dist | Format-Table Name, @{n = "Size (MB)"; e = { "{0:N1}" -f ($_.Length / 1MB) } }
