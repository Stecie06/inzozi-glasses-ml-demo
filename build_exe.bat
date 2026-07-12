@echo off
REM build_exe.bat
REM
REM FIX: earlier versions relied on 'python'/'pip' resolving to whatever
REM is on PATH at the time you run this - if the venv wasn't active (or
REM a system-wide Python came first on PATH), PyInstaller silently built
REM using the WRONG Python, one that doesn't have opencv installed,
REM which is exactly what caused
REM "ModuleNotFoundError: No module named 'cv2'" in the built .exe even
REM though `pip show opencv-python` inside the venv looked totally fine.
REM
REM This version calls the venv's OWN python.exe directly by path every
REM time, so it can't accidentally use the wrong interpreter no matter
REM what's active in your terminal.

REM Move to this script's own folder, so it works regardless of where
REM you double-click it from or what your current directory happens to be.
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
echo Confirming opencv-python (cv2) is visible to THIS interpreter:
"%VENV_PYTHON%" -c "import cv2; print('cv2 OK, version', cv2.__version__)"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: cv2 is not installed for %VENV_PYTHON%
    echo Run: %VENV_PYTHON% -m pip install opencv-python
    echo then re-run this script.
    echo ============================================================
    pause
    exit /b 1
)

echo Confirming deepface's dependencies (tf_keras) are visible:
"%VENV_PYTHON%" -c "import tf_keras; print('tf_keras OK')"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo ERROR: tf_keras is not installed for %VENV_PYTHON%
    echo Run: %VENV_PYTHON% -m pip install tf-keras
    echo then re-run this script. Without this, the packaged app's
    echo emotion detection will fail the same way it did before this
    echo was fixed when running from source.
    echo ============================================================
    pause
    exit /b 1
)
echo ============================================================

echo.
echo Installing/confirming PyInstaller in this same environment...
"%VENV_PYTHON%" -m pip install pyinstaller
if errorlevel 1 (
    echo FAILED: could not install pyinstaller
    pause
    exit /b 1
)

REM Clean any previous build so stale files (possibly built with the
REM wrong interpreter) don't get reused by mistake
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building with PyInstaller (via the venv's own interpreter)...
"%VENV_PYTHON%" -m PyInstaller smart_glasses.spec
if errorlevel 1 (
    echo FAILED: PyInstaller build failed - scroll up for the error
    pause
    exit /b 1
)

echo.
echo ============================================================
echo BUILD COMPLETE
echo ============================================================
echo Your app is in: dist\InzoziGlasses\
echo Zip that whole folder to share/submit it.
echo Run it by double-clicking dist\InzoziGlasses\InzoziGlasses.exe
echo ============================================================
pause