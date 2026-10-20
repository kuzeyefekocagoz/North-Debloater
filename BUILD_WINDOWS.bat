@echo off
setlocal EnableExtensions
cd /d "%~dp0"
taskkill /f /im adb.exe >nul 2>&1
taskkill /f /im NorthDebloater.exe >nul 2>&1
set "PYV=3.12.10"
set "PYEXE="

echo [1/5] Python araniyor...
for %%V in (3.12 3.13 3.11) do if not defined PYEXE for /f "delims=" %%P in ('py -%%V -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%P"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE (
  echo Python bulunamadi. Python %PYV% indiriliyor ve kullanici icin sessiz kuruluyor ^(yonetici izni gerekmez^)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest 'https://www.python.org/ftp/python/%PYV%/python-%PYV%-amd64.exe' -OutFile 'python-installer.exe'"
  if errorlevel 1 goto fail
  start /wait "" python-installer.exe /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_doc=0 Include_launcher=0
  del /q python-installer.exe >nul 2>&1
  if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)
if not defined PYEXE goto fail
echo Kullanilan Python: %PYEXE%

echo [2/5] Sanal ortam ve paketler kuruluyor ^(PySide6, PyInstaller^)...
if not exist ".venv\Scripts\python.exe" "%PYEXE%" -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail

echo [3/5] Android Platform-Tools indiriliyor ^(resmi Google kaynagi^)...
if not exist "platform-tools\adb.exe" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $ProgressPreference='SilentlyContinue'; Invoke-WebRequest 'https://dl.google.com/android/repository/platform-tools-latest-windows.zip' -OutFile 'platform-tools.zip'"
  if errorlevel 1 goto fail
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Force 'platform-tools.zip' '.'"
  if errorlevel 1 goto fail
)

echo [4/5] Uygulama paketleniyor...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --onedir --name NorthDebloater --add-data "platform-tools;platform-tools" --add-data "packages_db.json;." main.py
if errorlevel 1 goto fail
xcopy /E /I /Y "platform-tools" "dist\NorthDebloater\platform-tools" >nul
copy /Y "README_PORTABLE.txt" "dist\NorthDebloater\KULLANIM.txt" >nul

echo [5/5] ZIP olusturuluyor...
if exist "NorthDebloater-Windows-Portable.zip" del /q "NorthDebloater-Windows-Portable.zip"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Force 'dist\NorthDebloater' 'NorthDebloater-Windows-Portable.zip'"
if errorlevel 1 goto fail
echo.
echo TAMAM: NorthDebloater-Windows-Portable.zip olusturuldu.
echo Bu ZIP hedef bilgisayarda Python kurulumu gerektirmez. Cikarip NorthDebloater\NorthDebloater.exe dosyasini ac.
pause
exit /b 0

:fail
echo.
echo HATA: Islem tamamlanamadi. Internet baglantisini kontrol et ve tekrar dene.
pause
exit /b 1
