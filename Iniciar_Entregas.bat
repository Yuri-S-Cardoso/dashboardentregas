@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado. Consulte o README para preparar o sistema.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\iniciar_sistema.py" %*
if errorlevel 1 (
  echo.
  echo A inicializacao falhou. Leia a mensagem acima e consulte o README.
  pause
  exit /b 1
)
endlocal
