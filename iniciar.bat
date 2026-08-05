@echo off
REM Atalho para quem prefere nao usar a linha de comando.
REM Clique duas vezes neste arquivo.

cd /d "%~dp0"

echo ==========================================================
echo   NOVA REVISAO SISTEMATICA
echo ==========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: o Python nao foi encontrado.
    echo.
    echo Instale em https://www.python.org/downloads/
    echo IMPORTANTE: na primeira tela do instalador, marque a caixa
    echo "Add python.exe to PATH" antes de continuar.
    echo.
    pause
    exit /b 1
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Instalando a biblioteca necessaria ^(so na primeira vez^)...
    python -m pip install -r requirements.txt
    echo.
)

python iniciar_revisao.py

echo.
echo ==========================================================
echo   Terminou. A janela fica aberta para voce ler o resultado.
echo ==========================================================
pause
