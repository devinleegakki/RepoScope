@echo off
rem Launch RepoScope GUI against THIS repository (real git history, real numbers).
rem Double-click: the window opens and starts analysing this folder immediately.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment with Python 3.11 ...
    py -3.11 -m venv .venv
    if errorlevel 1 (
        echo.
        echo FAILED: cannot create .venv.
        echo Check installed interpreters with:  py -0p
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo [2/3] Installing PySide6, about 110 MB, please wait ...
    ".venv\Scripts\python.exe" -m pip install pyside6
    if errorlevel 1 (
        echo.
        echo FAILED to install PySide6. Run this manually:
        echo   .venv\Scripts\python.exe -m pip install pyside6
        pause
        exit /b 1
    )
)

echo [3/3] Analysing this repository with real git data ...
".venv\Scripts\python.exe" run_gui.py --path "%CD%"
if errorlevel 1 pause
