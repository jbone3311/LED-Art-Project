@echo off
REM Create virtual environment, activate it, and install dependencies
python -m venv venv
call .\venv\Scripts\activate.bat
pip install -r requirements.txt
@echo Virtual environment setup complete. 