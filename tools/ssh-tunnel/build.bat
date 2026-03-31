@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: Build SSH Tunnel GUI as a standalone Windows .exe
:: Requirements: Python 3.10+ and pip accessible in PATH
:: Run this once on your Windows machine to produce:  dist\SSHTunnel.exe
:: ─────────────────────────────────────────────────────────────────────────────

setlocal EnableDelayedExpansion

echo.
echo  [1/3] Installing / upgrading dependencies...
echo.
pip install --upgrade pip --quiet
pip install paramiko cryptography pyinstaller

echo.
echo  [2/3] Building executable (this may take a minute)...
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --name "SSHTunnel" ^
  tunnel_app.py

echo.
echo  [3/3] Done.
if exist "dist\SSHTunnel.exe" (
    echo.
    echo  SUCCESS — copy dist\SSHTunnel.exe anywhere and run it directly.
    echo  No Python installation required on the target machine.
    echo.
) else (
    echo.
    echo  FAILED — review the PyInstaller output above.
    echo.
)
pause
