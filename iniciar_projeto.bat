@echo off
chcp 65001 >nul
title Nexus - Sistema de Gestão de Reclamações
color 0A

echo ========================================
echo   Nexus - Iniciando o Projeto
echo ========================================
echo.

REM Verifica se está no diretório correto
if not exist "manage.py" (
    echo [ERRO] Arquivo manage.py não encontrado!
    echo Por favor, execute este script a partir da pasta raiz do projeto.
    pause
    exit /b 1
)

echo [1/3] Ativando ambiente virtual...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo ✓ Ambiente virtual ativado
) else (
    echo [AVISO] Ambiente virtual não encontrado!
    echo Continuando sem ambiente virtual...
)
echo.

echo [2/4] Verificando dependências...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado!
    echo Por favor, instale o Python 3.11+ e tente novamente.
    pause
    exit /b 1
)
echo ✓ Python encontrado
echo.

echo [3/4] Instalando/Atualizando dependências...
if exist "requirements.txt" (
    echo Instalando pacotes do requirements.txt...
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r requirements.txt
    echo ✓ Dependências instaladas
) else (
    echo [AVISO] Arquivo requirements.txt não encontrado!
)
echo.

echo [3.5/4] Atualizando notificações do sistema...
python manage.py seed_notifications
echo.

echo [4/5] Iniciando servidor Django...
echo ========================================
echo   Servidor rodando em: http://127.0.0.1:8000
echo   Abrindo navegador Chrome...
echo   Pressione Ctrl+C para parar o servidor
echo ========================================
echo.

REM Inicia o servidor Django em segundo plano e abre o Chrome
start /B python manage.py runserver

REM Aguarda 3 segundos para o servidor inicializar
timeout /t 3 /nobreak >nul

REM Abre o Chrome no endereço do servidor
echo [5/5] Abrindo Chrome...
start chrome http://127.0.0.1:8000

REM Aguarda o servidor continuar rodando
echo.
echo ✓ Servidor iniciado e navegador aberto!
echo.
python manage.py runserver

pause
