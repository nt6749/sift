@echo off
REM Medical Policy Extraction - Setup Script (Windows)
REM This script sets up both backend and frontend

setlocal enabledelayedexpansion

echo.
echo 🚀 Medical Policy Extraction - Setup Script (Windows)
echo =====================================================
echo.

REM Check Node.js
echo Checking Node.js...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Node.js not found. Please install Node.js 16+
    echo Download from: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo ✓ Node.js %NODE_VERSION%
echo.

REM Check Python
echo Checking Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python not found. Please install Python 3.8+
    echo Download from: https://www.python.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ %PYTHON_VERSION%
echo.

REM Setup Backend
echo Setting up Backend...
cd AI_Parser

if not exist "key.env" (
    echo.
    echo ⚠️  key.env not found
    echo Please create key.env with your Google Gemini API key:
    echo.
    echo   GEMINI_API_KEY=your_api_key_here
    echo.
    echo Get your API key from: https://ai.google.dev/
    echo.
    pause
)

if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -q -r requirements.txt

echo ✓ Backend setup complete
cd ..
echo.

REM Setup Frontend
echo Setting up Frontend...
cd frontend

echo Installing Node dependencies...
call npm install -q

echo ✓ Frontend setup complete
cd ..
echo.

REM Summary
echo.
echo ✓ Setup Complete!
echo =====================================================
echo.
echo Next steps:
echo.
echo 1. Edit AI_Parser\key.env with your Google Gemini API key
echo.
echo 2. Start the backend (in Command Prompt 1):
echo    cd AI_Parser
echo    venv\Scripts\activate.bat
echo    python app.py
echo.
echo 3. Start the frontend (in Command Prompt 2):
echo    cd frontend
echo    npm run dev
echo.
echo 4. Open http://localhost:3000 in your browser
echo.
echo For more help, see QUICKSTART.md
echo.
pause
