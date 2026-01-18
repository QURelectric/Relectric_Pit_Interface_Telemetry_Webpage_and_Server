@echo off
setlocal enabledelayedexpansion
pushd "%~dp0"


call ./Scripts/activate.bat

python3 -m uvicorn app.main:app --reload
