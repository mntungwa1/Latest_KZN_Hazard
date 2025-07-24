@echo off
echo -----------------------------------------
echo Cleaning Git repository and applying .gitignore...
echo -----------------------------------------

REM Remove index.lock if it exists
if exist .git\index.lock (
    del .git\index.lock
    echo Deleted stale index.lock file.
)

REM Remove all cached files so .gitignore can take effect
git rm -r --cached .
if %errorlevel% neq 0 (
    echo Failed to remove cached files. Exiting.
    pause
    exit /b %errorlevel%
)

REM Add all files (except ignored ones)
git add .

REM Commit the cleaned state
git commit -m "Clean repository and apply updated .gitignore"

REM Push changes to the remote main branch
git push origin main

echo -----------------------------------------
echo Done! Your repository is now clean.
echo -----------------------------------------
pause
