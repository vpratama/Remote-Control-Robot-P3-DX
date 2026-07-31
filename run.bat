@echo off
setlocal
set VENV_DIR=.venv

echo [1/2] Activating venv...
if not exist %VENV_DIR%\Scripts\activate.bat (
    echo ERROR: %VENV_DIR%\Scripts\activate.bat not found!
    echo Run setup.bat first to create the venv.
    pause
    exit /b 1
)

call %VENV_DIR%\Scripts\activate.bat

echo [2/2] Running main.py...
if not exist main.py (
    echo ERROR: main.py not found in current folder!
    pause
    exit /b 1
)

python main.py

echo.
echo Program exited.
pause