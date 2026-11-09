@echo off
:: Dashboard Escolar — Execucao automatica do Pipeline
:: Gerado automaticamente por scheduler.py

cd /d "C:\Users\Umbra\class_dashboard\backend"

:: Regista inicio
echo %date% %time% - Iniciando pipeline >> logs\scheduler.log 2>&1

:: Executa o pipeline Python
"C:\Python314\python.exe" pipeline.py >> logs\pipeline_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log 2>&1

:: Regista fim
echo %date% %time% - Pipeline concluido (codigo: %ERRORLEVEL%) >> logs\scheduler.log 2>&1
