@echo off
rem Double-click this file to install everything, build YTDownloader.exe and open the documentation.
title YTDownloader Setup
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
echo.
pause
