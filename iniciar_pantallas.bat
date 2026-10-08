@echo off
title Maschine MK3 Display Driver
cd /d "%~dp0"
echo Iniciando driver de pantallas Maschine MK3...
.venv\Scripts\python prototipo\dj_screens.py
pause
