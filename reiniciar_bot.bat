@echo off
title CartoonDex - Restart Automático

echo Fechando instancias antigas do bot...
taskkill /f /im python.exe >nul 2>&1

timeout /t 2 >nul

cd /d D:\CartoonDex

echo Iniciando CartoonDex atualizado...
python bot.py

pause