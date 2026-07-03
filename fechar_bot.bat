@echo off

echo Fechando instancias antigas do bot...
taskkill /f /im python.exe >nul 2>&1

timeout /t 2 >nul