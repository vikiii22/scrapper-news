@echo off
REM Script para ejecutar scrapper-soccerdata.py con el entorno virtual correcto
cd /d "%~dp0"
.venv\Scripts\python.exe scrapper\scrapper-soccerdata.py
pause
