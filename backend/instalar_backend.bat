@echo off
:: ============================================================================
:: DASHBOARD ESCOLAR — INSTALADOR COMPLETO DO BACKEND AUTOMÁTICO
:: ============================================================================
:: Execute este ficheiro como ADMINISTRADOR na primeira instalação.
:: Ele irá:
::   1. Verificar o Python e instalar dependências
::   2. Instalar os browsers do Playwright (Chromium)
::   3. Configurar as tarefas automáticas diárias (07:30 e 18:00)
::   4. Fazer uma execução de teste imediata
:: ============================================================================

title Dashboard Escolar — Instalador do Backend

cd /d "%~dp0"

echo.
echo ============================================================
echo   DASHBOARD ESCOLAR — CONFIGURACAO DO BACKEND AUTOMATICO
echo ============================================================
echo.

:: --- Verifica Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale Python 3.11+ em python.org
    pause
    exit /b 1
)
echo [OK] Python encontrado.

:: --- Instala dependências Python ---
echo.
echo [1/4] A instalar dependencias Python...
pip install playwright google-generativeai gspread google-auth python-dotenv --quiet
if errorlevel 1 (
    echo [AVISO] Algumas dependencias podem nao ter instalado. Continuando...
)

:: --- Instala Chromium para Playwright ---
echo.
echo [2/4] A instalar Chromium (Playwright)...
python -m playwright install chromium
if errorlevel 1 (
    echo [AVISO] Erro ao instalar Chromium. Tente manualmente: playwright install chromium
)

:: --- Verifica o ficheiro .env ---
echo.
echo [3/4] A verificar configuracao (.env)...
if not exist ".env" (
    echo [AVISO] Ficheiro .env nao encontrado!
    echo         Copie .env.example para .env e preencha os dados.
    copy .env.example .env >nul 2>&1
    echo         Ficheiro .env criado a partir do exemplo.
    echo         EDITE o ficheiro .env antes de continuar!
    pause
)
echo [OK] Ficheiro .env encontrado.

:: --- Instala tarefas no Windows Task Scheduler ---
echo.
echo [4/4] A instalar tarefas automaticas (07:30 e 18:00)...
python scheduler.py install
if errorlevel 1 (
    echo [AVISO] Erro ao instalar tarefas. Tente correr como Administrador.
)

echo.
echo ============================================================
echo   INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo   Proximas execucoes automaticas:
echo     - Manha:  07:30 (antes de ir para a escola)
echo     - Tarde:  18:00 (ao chegar a casa)
echo.
echo   Para executar agora (teste):
echo     python pipeline.py --dry-run
echo.
echo   Para ver os logs:
echo     type logs\scheduler.log
echo.
pause

