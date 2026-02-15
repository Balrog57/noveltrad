@echo off
call venv\Scripts\activate
set PYTHONPATH=%PYTHONPATH%;%CD%
python src/main.py
pause
