@echo off
rem Compila CVLaTeX a un .exe autocontenido (dist\CVLaTeX_Windows.exe)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pyinstaller --noconfirm --onefile --windowed --name CVLaTeX ^
  --icon "assets\CVLaTex.ico" ^
  --add-data "web;web" ^
  --add-data "templates;templates" ^
  main.py
if errorlevel 1 exit /b 1
if not exist "dist\CVLaTeX.exe" (
  echo Error: PyInstaller no genero dist\CVLaTeX.exe 1>&2
  exit /b 1
)
move /Y "dist\CVLaTeX.exe" "dist\CVLaTeX_Windows.exe"
if errorlevel 1 (
  echo Error: could not rename dist\CVLaTeX.exe to dist\CVLaTeX_Windows.exe 1>&2
  exit /b 1
)
echo.
echo Listo: dist\CVLaTeX_Windows.exe
pause