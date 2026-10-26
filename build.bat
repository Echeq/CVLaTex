@echo off
rem Build CVLaTeX on Windows.
rem
rem Creates/reuses .venv, stages only the public runtime assets
rem (web\ + the 12 template .tex files) under build\stage, generates a Windows
rem version resource from version.py and runs PyInstaller against the staged
rem tree. The release archive is produced by tools\package_release.py:
rem   dist\CVLaTeX-v<version>-windows-x64.zip (contains CVLaTeX.exe)
rem The raw dist\CVLaTeX.exe stays available for local runs.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Creating .venv...
  python -m venv .venv
  if errorlevel 1 goto :fail
)
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

python -c "import docx, PyInstaller" >nul 2>&1
if errorlevel 1 (
  python -m pip install --upgrade pip
  if errorlevel 1 goto :fail
  python -m pip install -r requirements.txt
  if errorlevel 1 goto :fail
)

python tools\stage_assets.py --dest build\stage
if errorlevel 1 goto :fail

python tools\windows_version.py --out build\windows_version.txt
if errorlevel 1 goto :fail

pyinstaller --noconfirm --onefile --windowed --name CVLaTeX ^
  --icon "%CD%\assets\CVLaTex.ico" ^
  --version-file "build\windows_version.txt" ^
  --distpath dist --workpath build\pyinstaller --specpath build ^
  --add-data "%CD%\build\stage\web;web" ^
  --add-data "%CD%\build\stage\templates;templates" ^
  --add-data "%CD%\build\stage\assets;assets" ^
  "%CD%\main.py"
if errorlevel 1 goto :fail

if not exist "dist\CVLaTeX.exe" (
  echo Error: PyInstaller did not create dist\CVLaTeX.exe 1>&2
  goto :fail
)

python tools\package_release.py --platform windows --binary "dist\CVLaTeX.exe"
if errorlevel 1 goto :fail

echo.
echo Done: versioned Windows archive in dist\ (raw binary: dist\CVLaTeX.exe)
if /I not "%CI%"=="true" pause
exit /b 0

:fail
echo Error: CVLaTeX build failed 1>&2
if /I not "%CI%"=="true" pause
exit /b 1
