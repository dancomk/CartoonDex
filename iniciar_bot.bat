@echo off
title CartoonDex Bot

echo ===============================
echo Iniciando CartoonDex com Python...
echo ===============================

cd /d D:\CartoonDex

if not exist bot.py (
    echo.
    echo [ERRO] bot.py nao encontrado na pasta D:\CartoonDex
    pause
    exit
)

echo.
echo Executando: python bot.py
echo.

python bot.py

echo.
echo ===============================
echo Bot encerrado ou ocorreu um erro.
echo Verifique as mensagens acima.
echo ===============================
pause