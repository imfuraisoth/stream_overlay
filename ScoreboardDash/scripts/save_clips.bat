@echo off
set CURRENT_DIR=%~dp0
set FILE_PATH=%CURRENT_DIR%\pyclient.py
python.exe %FILE_PATH% "-saveclips"
pause