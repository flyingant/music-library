@echo off
REM Unified Music Library Launcher for Windows
REM ==========================================
REM Launches the unified web interface with automatic setup and environment management

echo.
echo ==========================================
echo    MaYi's Music Library Management System
echo ==========================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Function to check if Python 3 is available
:check_python
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3 from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

python --version 2>&1 | findstr "Python 3" >nul
if %errorlevel% neq 0 (
    echo ERROR: Python 3 is required but not found!
    echo Please install Python 3 from https://python.org
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found: %PYTHON_VERSION%
echo.

REM Function to create virtual environment
:create_venv
set "VENV_NAME=music_env_windows"
if not exist "%VENV_NAME%" (
    echo Creating virtual environment for Windows...
    python -m venv %VENV_NAME%
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment!
        echo Please ensure you have the 'venv' module installed.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully: %VENV_NAME%
) else (
    echo Virtual environment already exists: %VENV_NAME%
)
echo.

REM Function to activate virtual environment
:activate_venv
echo Activating virtual environment...
call %VENV_NAME%\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment!
    pause
    exit /b 1
)
echo Virtual environment activated: %VENV_NAME%
echo.

REM Function to install requirements
:install_requirements
if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo WARNING: Failed to install dependencies from requirements.txt!
        echo Trying to install core dependencies manually...
        pip install flask flask-cors mutagen pillow cryptography requests
        if %errorlevel% neq 0 (
            echo ERROR: Failed to install dependencies!
            pause
            exit /b 1
        )
    )
    echo Dependencies installed successfully!
) else (
    echo WARNING: requirements.txt not found, installing core dependencies...
    pip install flask flask-cors mutagen pillow cryptography requests
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install core dependencies!
        pause
        exit /b 1
    )
    echo Core dependencies installed successfully!
)
echo.

REM Function to check dependencies
:check_dependencies
echo Checking dependencies...
python -c "import flask, flask_cors, mutagen, PIL, cryptography, requests" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Missing dependencies detected!
    echo Installing required packages...
    pip install flask flask-cors mutagen pillow cryptography requests
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
)
echo All dependencies are available!
echo.

REM Function to setup directories
:setup_directories
echo Setting up directories...
cd ..
if not exist "Library" mkdir Library
if not exist "New" mkdir New
if not exist "Duplicate" mkdir Duplicate
if not exist "Trash" mkdir Trash
if not exist "Unlocked" mkdir Unlocked
cd "%SCRIPT_DIR%"
if not exist "thumbnails" mkdir thumbnails
echo Directories created successfully!
echo.

REM Launch the unified web interface
echo ==========================================
echo    Launching unified web interface...
echo ==========================================
echo.
echo Opening browser in 3 seconds...
echo Press Ctrl+C to stop the server
echo.

REM Open browser after a short delay
timeout /t 3 /nobreak >nul
start http://localhost:8088

REM Launch the Python script
python launch_unified.py

REM Keep the window open if there's an error
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start the web interface!
    echo Please check the error messages above.
    pause
)
