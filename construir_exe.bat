@echo off
rem Compila el ejecutable autocontenido en dist\MaschineMK3AsPush\
cd /d "%~dp0"

echo [1/3] Instalando dependencias de compilacion...
.venv\Scripts\pip install -q pyinstaller

echo [2/3] Generando icono...
.venv\Scripts\python prototipo\hacer_icono.py

echo [3/3] Compilando con PyInstaller...
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onedir --noconsole --name MaschineMK3AsPush ^
  --icon prototipo\icono.ico --paths prototipo ^
  --add-data "prototipo\config.example.json;." ^
  --collect-all libusb_package --hidden-import mido.backends.rtmidi --hidden-import rtmidi ^
  prototipo\maschine_mk3.py

echo.
echo [+] Compilacion completada con exito en: dist\MaschineMK3AsPush\MaschineMK3AsPush.exe
pause
