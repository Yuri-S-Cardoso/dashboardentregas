@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente virtual nao encontrado. Consulte o README.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "scripts\iniciar_online.py" %*
if errorlevel 1 (
  echo.
  echo O acesso online nao foi iniciado. Leia a mensagem acima e docs\ACESSO_NGROK.md.
  pause
  exit /b 1
)
endlocal
