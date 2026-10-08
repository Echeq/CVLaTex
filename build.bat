@echo off
rem Compila CVLaTeX a un .exe autocontenido (dist\CVLaTeX.exe)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pyinstaller --noconfirm --onefile --windowed --name CVLaTeX ^
  --add-data "web;web" ^
  --add-data "templates;templates" ^
  main.py
echo.
echo Listo: dist\CVLaTeX.exe
pause