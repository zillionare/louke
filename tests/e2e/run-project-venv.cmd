@echo off
setlocal
set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"
set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  >&2 echo %PYTHON%: project-venv Python is missing or not executable
  exit /b 127
)
"%PYTHON%" "%ROOT%\tests\e2e\run_e2e.py" %*
exit /b %ERRORLEVEL%
