@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r server\requirements.txt
if errorlevel 1 goto error
start "" http://localhost:7654
cd server
..\.venv\Scripts\python.exe server.py
pause
exit /b
:error
echo Se requiere Python 3.11 o superior e Internet para instalar dependencias.
pause
