#!/bin/bash
# Script para ejecutar scrapper-soccerdata.py con el entorno virtual correcto
cd "$(dirname "$0")"
.venv/Scripts/python.exe scrapper/scrapper-soccerdata.py
