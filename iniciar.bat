@echo off
setlocal enabledelayedexpansion
REM Atalho para quem prefere nao usar a linha de comando.
REM Clique duas vezes neste arquivo.

cd /d "%~dp0"

echo ==========================================================
echo   NOVA REVISAO SISTEMATICA
echo ==========================================================
echo.

REM Procura o Python em varios lugares. `python` pode nao estar no PATH da
REM sessao — tipicamente quando a janela foi aberta antes de o Python ser
REM instalado, ja que alteracoes de PATH so valem para processos novos.
set "PY="

python --version >nul 2>&1
if not errorlevel 1 set "PY=python"

if not defined PY (
    py --version >nul 2>&1
    if not errorlevel 1 set "PY=py"
)

if not defined PY (
    for %%D in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%ProgramFiles%\Python313\python.exe"
        "%ProgramFiles%\Python312\python.exe"
    ) do (
        if not defined PY if exist %%D set "PY=%%D"
    )
)

if not defined PY (
    echo ERRO: nao encontrei o Python nesta maquina.
    echo.
    echo Instale em https://www.python.org/downloads/
    echo IMPORTANTE: na primeira tela do instalador, marque a caixa
    echo "Add python.exe to PATH" antes de continuar.
    echo.
    pause
    exit /b 1
)

echo Usando: %PY%
echo.

%PY% -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Instalando a biblioteca necessaria ^(so na primeira vez^)...
    %PY% -m pip install -r requirements.txt
    echo.
)

%PY% iniciar_revisao.py

echo.
echo ==========================================================
echo   Terminou. A janela fica aberta para voce ler o resultado.
echo ==========================================================
pause
