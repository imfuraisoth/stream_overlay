@echo off

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo Installing requirements...
    pip install -r requirements.txt
) else (
    echo Virtual environment found.
    call venv\Scripts\activate
)

python pyserver.py -w

pause