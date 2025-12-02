@echo off 
cd /d "c:\Users\Shivaay Dhondiyal\Desktop\shivaay\coding\2_projects\25_murf_ai\elderly_care\murfai\frontend" 
if not exist ".env.local" echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local 
npm run dev 
pause 
