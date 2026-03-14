@echo off

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing requirements...
python -m pip install -r requirements.txt

python pyserver.py

pause