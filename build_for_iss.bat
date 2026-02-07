@echo off
echo ========================================================
echo  TaskFlow v5.0 - Build & Installer
echo ========================================================
echo.

echo [1/5] Cleaning workspace...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
if exist *.spec del /q *.spec

echo.
echo [2/5] Installing dependencies...
pip install --upgrade pyinstaller requests PyQt6 keyboard

echo.
echo [3/5] Building Executable (PyInstaller)...
pyinstaller --noconfirm --onedir --windowed --noconsole --clean --name "TaskFlow" --add-data "README.md;." "TaskFlow.py"

echo.
echo [4/5] Building Installer (Inno Setup)...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% "setup.iss" /O"dist"
    echo.
    echo ========================================================
    echo  BUILD SUCCESSFUL!
    echo  Installer: dist\TaskFlow_Setup_v5.0.exe
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo  WARNING: Inno Setup Compiler not found at default path.
    echo  Please open "setup.iss" manually and click Compile.
    echo ========================================================
)
pause