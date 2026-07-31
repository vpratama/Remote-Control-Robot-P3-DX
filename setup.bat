@echo off
setlocal
set VENV_DIR=.venv
set PYTHON_VERSION=3.12

echo [1/5] Removing existing venv folder...
if exist %VENV_DIR% (
    echo Found existing %VENV_DIR%, removing...
    call %VENV_DIR%\Scripts\deactivate.bat 2>nul
    rmdir /s /q %VENV_DIR%
    if exist %VENV_DIR% (
        echo Failed to remove %VENV_DIR%. Close VS Code / terminals using it and try again.
        pause
        exit /b 1
    )
    echo Removed old %VENV_DIR%.
) else (
    echo No existing %VENV_DIR% found, skipping.
)

echo.
echo [2/5] Installing uv using pip...
python -m pip install --upgrade pip
python -m pip install --upgrade uv
if %ERRORLEVEL% NEQ 0 (
    echo python command failed, trying py launcher...
    py -3 -m pip install --upgrade pip
    py -3 -m pip install --upgrade uv
)

echo.
echo [3/5] Installing Python %PYTHON_VERSION% inside venv using uv...
uv python install %PYTHON_VERSION%
uv venv %VENV_DIR% --python %PYTHON_VERSION%

echo.
echo [4/5] Activating venv...
call %VENV_DIR%\Scripts\activate.bat

echo.
echo [5/5] Installing packages from requirements.txt...
if exist requirements.txt (
    uv pip install -r requirements.txt
) else (
    echo requirements.txt not found, skipping.
)

echo.
echo ==========================================
echo Setup complete! Venv '%VENV_DIR%' is active.
python --version
echo ==========================================

cmd /k