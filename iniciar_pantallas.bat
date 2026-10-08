@echo off
title Maschine MK3 Display Driver
cd /d "%~dp0"
echo Iniciando driver de pantallas Maschine MK3...
echo Para salir, cerra esta ventana.
:inicio
.venv\Scripts\python prototipo\dj_screens.py
echo.
echo El programa se cerro; lo vuelvo a abrir en 3 segundos (cerra esta ventana para salir).
timeout /t 3 /nobreak >nul
goto inicio
