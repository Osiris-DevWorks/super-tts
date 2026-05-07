@echo off
echo ========================================
echo Super TTS - Build Script
echo ========================================
echo.

echo Step 1: Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo   - Old builds removed
echo.

echo Step 2: Installing PyInstaller + PyQt6 (if needed)...
.venv\Scripts\python.exe -m pip install pyinstaller PyQt6 --quiet
if errorlevel 1 (
    echo WARNING: Could not install PyInstaller / PyQt6 into .venv
    echo Please install manually:
    echo     .venv\Scripts\pip install pyinstaller PyQt6
    pause
)
echo   - PyInstaller + PyQt6 ready
echo.

echo Step 3: Building executable...
.venv\Scripts\python.exe scripts\build\build_exe.py
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)
echo   - Executable created
echo.

echo Step 4: Verifying onedir build...
rem cmd's `if exist` doesn't expand wildcards on directories — read VERSION.TXT
rem and check the exact folder name instead. Without this, a successful
rem PyInstaller build still falsely reported "Build folder not found".
set /p APPVER=<VERSION.TXT
if exist "dist\Super-TTS-v%APPVER%\" (
    echo   - Build folder exists: dist\Super-TTS-v%APPVER%\
) else (
    echo   - ERROR: Build folder not found at dist\Super-TTS-v%APPVER%\
    pause
    exit /b 1
)
echo.

echo Step 5: Creating installer (requires Inno Setup)...
set "ISCC_EXE="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if defined ISCC_EXE (
    echo   Using "%ISCC_EXE%"
    "%ISCC_EXE%" installer.iss
    if errorlevel 1 (
        echo WARNING: Installer creation failed
        echo You can create it manually with Inno Setup
    ) else (
        echo   - Installer created successfully!
    )
) else (
    echo WARNING: Inno Setup not found in any of:
    echo     C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    echo     C:\Program Files\Inno Setup 6\ISCC.exe
    echo     %%LOCALAPPDATA%%\Programs\Inno Setup 6\ISCC.exe
    echo Skipping installer creation
    echo Install Inno Setup from: https://jrsoftware.org/isdl.php
    echo Or create the installer manually by opening installer.iss
)
echo.

echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Outputs:
for %%f in (dist\Super-TTS-*-Setup.exe) do (
    echo   [OK] Installer: %%f
)
echo.
echo Next steps:
echo   1. Test the installer: dist\Super-TTS-*-Setup.exe
echo   2. Upload the installer to GitHub releases
echo.
pause
