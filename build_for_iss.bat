@echo off
echo ========================================================
echo  TaskFlow v2.5 - Build
echo ========================================================
echo.

echo [1/4] Installing dependencies...
pip install pyinstaller requests PyQt6 keyboard

echo.
echo [2/4] Cleaning workspace...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [3/4] Building Executable (PyInstaller)...
pyinstaller --noconfirm --onedir --windowed --clean --name "TaskFlow" "TaskFlow.py"

echo.
echo [4/4] Building Installer (Inno Setup)...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    %ISCC% "setup.iss"
    echo.
    echo ========================================================
    echo  BUILD SUCCESSFUL!
    echo  Installer: TaskFlow_Setup_v2.5.exe
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo  WARNING: Inno Setup Compiler not found at default path.
    echo  Please open "setup.iss" manually and click Compile.
    echo ========================================================
)
pause