@echo off
rem Launch RepoScope GUI with the built-in demo dataset.
rem Uses a local .venv created from Python 3.11, so it does not depend on
rem whatever "python" resolves to in PATH (on some machines that is a
rem Windows Store placeholder that silently does nothing).
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

echo [3/3] Starting RepoScope ...
".venv\Scripts\python.exe" run_gui.py --demo
if errorlevel 1 pause
