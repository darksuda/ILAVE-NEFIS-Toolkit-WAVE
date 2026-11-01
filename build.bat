@echo off
setlocal

echo ==========================================
echo ILAVE NEFIS Toolkit - WAVE MODULE
echo Windows Build
echo ==========================================

call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo ERROR: Could not activate virtual environment.
    pause
    exit /b 1
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name "ILAVE NEFIS Toolkit - WAVE MODULE" ^
    --collect-all cartopy ^
    --collect-all rasterio ^
    --collect-all matplotlib ^
    main.py

if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo BUILD COMPLETED.
echo Check the dist folder.
pause
