@echo off
echo Starting TimerPro LEGACY version (Monolithic)...
cd /d "%~dp0"
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
pause
