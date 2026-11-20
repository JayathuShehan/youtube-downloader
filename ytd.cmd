@echo off
rem Short alias: "ytd -url" / "ytd -ui" runs YTDownloader.exe.
rem Looks next to this file first, then in a "dist" subfolder (project folder layout).
if exist "%~dp0YTDownloader.exe" (
    "%~dp0YTDownloader.exe" %*
) else if exist "%~dp0dist\YTDownloader.exe" (
    "%~dp0dist\YTDownloader.exe" %*
) else (
    echo YTDownloader.exe was not found next to ytd.cmd or in "%~dp0dist".
    echo Build it with:  powershell -ExecutionPolicy Bypass -File build.ps1
    exit /b 1
)
