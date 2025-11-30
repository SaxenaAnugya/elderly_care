@echo off
REM =====================================================
REM Run both backend and frontend in separate cmd windows
REM This script writes minimal helper scripts and launches them.
REM =====================================================

cd /d "%~dp0"

echo Starting Loneliness Companion (backend + frontend)
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000 (Next may auto-select another free port)

REM Create a simple backend starter script (temp_backend.bat)
echo @echo off > temp_backend.bat
echo cd /d "%~dp0" >> temp_backend.bat
echo if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat" >> temp_backend.bat
echo if exist "backend\venv\Scripts\activate.bat" call "backend\venv\Scripts\activate.bat" >> temp_backend.bat
echo python backend\api_server.py >> temp_backend.bat
echo pause >> temp_backend.bat

REM Create a simple frontend starter script (temp_frontend.bat)
echo @echo off > temp_frontend.bat
echo cd /d "%~dp0frontend" >> temp_frontend.bat
echo if not exist ".env.local" echo NEXT_PUBLIC_API_URL=http://localhost:8000 ^> .env.local >> temp_frontend.bat
echo npm run dev >> temp_frontend.bat
echo pause >> temp_frontend.bat

REM Start backend in a new window (keeps the window open)
start "Backend Server" cmd /k "%CD%\temp_backend.bat"

REM Small wait to give backend a head start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
start "Frontend Server" cmd /k "%CD%\temp_frontend.bat"

echo.
echo Started backend and frontend in new windows.
echo If Next.js chooses a different port (e.g. 3001) it will be shown in the frontend terminal.
echo Temporary helper scripts: temp_backend.bat, temp_frontend.bat

exit /b 0
