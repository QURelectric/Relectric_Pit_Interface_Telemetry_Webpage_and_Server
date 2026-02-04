@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"


call ./Scripts/activate.bat

echo Checking and installing dependencies
pip install -r requirements.txt --quiet --no-warn-script-location
echo Done

python3 -m uvicorn app.main:app

pause
