@echo off 
cd /d "C:\Users\Shivaay Dhondiyal\Desktop\shivaay\coding\2_projects\25_murf_ai\elderly_care\murfai\" 
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat" 
if exist "backend\venv\Scripts\activate.bat" call "backend\venv\Scripts\activate.bat" 
python backend\api_server.py 
pause 
