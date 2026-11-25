@echo off
setlocal
set "project=%~dp0"
if exist "%project%run.py" if exist "%project%src\app\views.py" goto found
set "project=%USERPROFILE%\Documents\ChatGPT\PostCode\"
if exist "%project%run.py" if exist "%project%src\app\views.py" goto found
echo Project files were not found. Extract PostCode-MVP.zip and open start.cmd inside the extracted folder.
pause
exit /b 1
:found
cd /d "%project%" || exit /b 1
python --version >nul 2>&1
if errorlevel 1 goto pylauncher
python "%project%run.py" --open-browser
goto done
:pylauncher
py -3 "%project%run.py" --open-browser
:done
if errorlevel 1 pause
