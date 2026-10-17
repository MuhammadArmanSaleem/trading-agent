@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 app.py
) else (
    python app.py
)
if errorlevel 1 (
    echo.
    echo Install Python 3.10 or newer with Tcl/Tk enabled, then try again.
    pause
)
