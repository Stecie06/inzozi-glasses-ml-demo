@echo off
REM build_exe.bat
REM
REM FIX: The previous version had a syntax error in the :check_import
REM subroutine due to parentheses being used incorrectly. This version
REM fixes that and ensures all dependencies are properly verified.

cd /d "%~dp0"

set VENV_PYTHON=smartglasses_env\Scripts\python.exe

if not exist "%VENV_PYTHON%" (
    echo ============================================================
    echo ERROR: Could not find %VENV_PYTHON%
    echo Make sure this .bat file is in the same folder as your
    echo smartglasses_env virtual environment folder.
    echo ============================================================
    pause
    exit /b 1
)

echo ============================================================
echo Using this Python interpreter (must be inside smartglasses_env):
"%VENV_PYTHON%" -c "import sys; print(sys.executable)"
echo ============================================================

echo.
echo Installing everything from requirements.txt into THIS environment...
"%VENV_PYTHON%" -m pip install -r requirements.txt --retries 5 --timeout 100
if errorlevel 1 (
    echo ============================================================
    echo First attempt failed. Retrying with --no-cache-dir...
    echo ============================================================
    "%VENV_PYTHON%" -m pip cache purge
    "%VENV_PYTHON%" -m pip install -r requirements.txt --retries 5 --timeout 100 --no-cache-dir
    if errorlevel 1 (
        echo ============================================================
        echo ERROR: pip install failed twice. Scroll up for the error.
        echo ============================================================
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo Verifying every dependency the app actually needs...
echo ============================================================
set ALL_OK=1

"%VENV_PYTHON%" -c "import cv2" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] cv2 ^(pip package: opencv-python^)
    set ALL_OK=0
) else (
    echo   [OK]     cv2
)

"%VENV_PYTHON%" -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] numpy
    set ALL_OK=0
) else (
    echo   [OK]     numpy
)

"%VENV_PYTHON%" -c "import face_recognition" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] face_recognition
    set ALL_OK=0
) else (
    echo   [OK]     face_recognition
)

"%VENV_PYTHON%" -c "import ultralytics" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] ultralytics
    set ALL_OK=0
) else (
    echo   [OK]     ultralytics
)

"%VENV_PYTHON%" -c "import deepface" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] deepface
    set ALL_OK=0
) else (
    echo   [OK]     deepface
)

"%VENV_PYTHON%" -c "import pyttsx3" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] pyttsx3
    set ALL_OK=0
) else (
    echo   [OK]     pyttsx3
)

"%VENV_PYTHON%" -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] serial ^(pip package: pyserial^)
    set ALL_OK=0
) else (
    echo   [OK]     serial
)

"%VENV_PYTHON%" -c "import pkg_resources" >nul 2>&1
if errorlevel 1 (
    echo   [FAILED] pkg_resources ^(pip package: setuptools^)
    set ALL_OK=0
) else (
    echo   [OK]     pkg_resources
)

if "%ALL_OK%"=="0" (
    echo ============================================================
    echo STOPPING: one or more dependencies above FAILED to import.
    echo Install the missing packages and run this script again.
    echo ============================================================
    pause
    exit /b 1
)

echo ============================================================
echo All dependencies verified OK. Proceeding to build.
echo ============================================================

echo.
echo Installing/confirming PyInstaller in this same environment...
"%VENV_PYTHON%" -m pip install pyinstaller
if errorlevel 1 (
    echo FAILED: could not install pyinstaller
    pause
    exit /b 1
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building with PyInstaller...
"%VENV_PYTHON%" -m PyInstaller smart_glasses.spec
if errorlevel 1 (
    echo FAILED: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD COMPLETE
echo ============================================================
echo Your app is in: dist\InzoziGlasses\
echo Run it by double-clicking dist\InzoziGlasses\InzoziGlasses.exe
echo ============================================================
pause
exit /b 0