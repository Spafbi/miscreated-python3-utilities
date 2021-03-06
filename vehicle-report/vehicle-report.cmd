@echo off
pushd "%~dp0"
chcp 65001>nul
set BASEPATH=%~dp0
set BASEPATH=%BASEPATH:~0,-1%

if NOT "%BASEPATH%"=="%BASEPATH: =%" goto :noSpaces

set CORESCRIPT=%BASEPATH%\vehicle-report.py
set PYTHONURL=https://www.python.org/ftp/python/3.9.4/python-3.9.4-embed-amd64.zip
set PYTHONDIR=%BASEPATH%\python
set PYTHONBIN=%PYTHONDIR%\python.exe
set PIPBIN=%PYTHONDIR%\Scripts\pip.exe
set PIPURL=https://bootstrap.pypa.io/get-pip.py
set SMSSTEMP=%BASEPATH%\temp
goto :pythonCheck

:pythonCheck
if exist "%PYTHONBIN%" goto :importSite
echo Downloading and installing embedded Python...
if not exist "%SMSSTEMP%" (
  md "%SMSSTEMP%"
)
curl -L %PYTHONURL% -o "%SMSSTEMP%/python.zip"
powershell Expand-Archive -LiteralPath '%SMSSTEMP%/python.zip' -DestinationPath '%PYTHONDIR%'
goto :importSite

:importSite
setlocal
>%PYTHONDIR%\python39._pth (
    for %%I in (
        "python39.zip"
        "."
        ""
        "import site"
    ) do echo %%~I
)
goto :pipCheck

:pipCheck
if exist "%PIPBIN%" goto :runScript
echo Setting up Python pip...
curl -L %PIPURL% -o "%SMSSTEMP%/get-pip.py"
"%PYTHONBIN%" "%SMSSTEMP%/get-pip.py" --no-warn-script-location
goto :runScript

:runScript
"%PYTHONBIN%" %CORESCRIPT%
goto :end

:noSpaces
echo This script cannot be run from a path having spaces.
echo     %BASEPATH%
goto :end

:end
pause