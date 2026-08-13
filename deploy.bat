@echo off
setlocal EnableDelayedExpansion

echo.
echo [0/6] Pre-flight checks...

rem Ensure required tools are available
where ssh >nul 2>&1 || (
    echo ERROR: `ssh` not found in PATH. Install OpenSSH client.
    exit /b 1
)
where npm >nul 2>&1 || (
    echo ERROR: `npm` not found in PATH. Install Node.js/npm.
    exit /b 1
)

rem Ensure git working tree is clean to avoid accidental commits/pushes
rem You can skip this check by setting SKIP_GIT_CHECK=1 in environment or passing --force
if "%1"=="--force" (
    set SKIP_GIT_CHECK=1
)
if not defined SKIP_GIT_CHECK (
    set GIT_DIRTY=
    for /f "usebackq delims=" %%s in (`git status --porcelain`) do (
        set GIT_DIRTY=1
        set "LINE=%%s"
        setlocal enabledelayedexpansion
        set "FILE=!LINE:~3!"
        endlocal & call :append_changed "%%~s"
    )
    if defined GIT_DIRTY (
        rem If only safe files changed, auto-commit them
        call :check_and_autocommit
        if errorlevel 1 (
            echo ERROR: Git working tree is not clean. Commit or stash changes before running this deploy script.
            echo To bypass this check (unsafe), run: deploy.bat --force
            git status --porcelain
            exit /b 1
        )
    )
) else (
    echo Warning: SKIP_GIT_CHECK is set; continuing despite uncommitted changes.
)

rem helper to accumulate changed files
:append_changed
setlocal EnableDelayedExpansion
set "LINE=%~1"
set "FILE=!LINE:~3!"
>>"%TEMP%\deploy_changed_files.txt" echo !FILE!
endlocal
exit /b 0

:check_and_autocommit
rem Define whitelist of safe files (space-separated)
set SAFE_LIST=deploy.bat website\package.json app\repositories\mongodb\mongo.py
if not exist "%TEMP%\deploy_changed_files.txt" exit /b 1
set BAD=0
for /f "usebackq delims=" %%f in ("%TEMP%\deploy_changed_files.txt") do (
    set "FOUND=0"
    for %%s in (%SAFE_LIST%) do if /I "%%~f"=="%%~s" set FOUND=1
    if "%%~f"=="" set FOUND=1
    if %%FOUND%%==0 set BAD=1
)
if %BAD%==1 exit /b 1
rem All changed files are safe; commit them automatically
for /f "usebackq delims=" %%f in ("%TEMP%\deploy_changed_files.txt") do (
    git add "%%~f"
)
git commit -m "Auto-commit: safe changes before deploy" || exit /b 1
del "%TEMP%\deploy_changed_files.txt" >nul 2>&1
exit /b 0

echo.
echo [1/6] Building website locally...

cd website
echo Installing dependencies...
call npm ci

echo Building website...
call npm run build

if errorlevel 1 (
    echo ERROR: Website build failed.
    exit /b 1
)

if not exist out\index.html (
    echo ERROR: Build did not produce out\index.html
    exit /b 1
)

cd ..

echo.
echo [2/6] Preparing git push (no auto-commit)...

rem At this point the working tree must be clean. Determine current branch.
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
echo Current branch: %BRANCH%

git config --local credential.username Hunters1ar >nul 2>&1 || echo "Warning: git config failed"

echo.
echo [3/6] Pushing changes to remote (%BRANCH%)...

git push origin %BRANCH% || (
    echo ERROR: Git push failed. You may need to resolve remote issues interactively.
    exit /b 1
)

echo.
echo [4/6] Deploying website to Vercel (recommended for UI hosting)...

cd website
where vercel >nul 2>&1 || (
    echo ERROR: Vercel CLI not found. Install with `npm i -g vercel` or set PATH.
    exit /b 1
)

if defined VERCEL_TOKEN (
    echo Using non-interactive Vercel deploy (token provided).
    vercel --prod --token %VERCEL_TOKEN% --confirm || (
        echo ERROR: Vercel deploy failed.
        exit /b 1
    )
) else (
    echo VERCEL_TOKEN not set. Running interactive vercel deploy (may prompt for login).
    vercel --prod --confirm || (
        echo ERROR: Vercel deploy failed.
        exit /b 1
    )
)
cd ..

echo.
echo [5/6] Uploading SSH public key (if available) and updating backend on VPS...

set REMOTE_HOST=root@134.209.75.49

rem determine public key file to upload
if exist .ssh\deploy_id_rsa.pub (
    set PUBKEY=.ssh\deploy_id_rsa.pub
) else if exist %USERPROFILE%\.ssh\id_rsa.pub (
    set PUBKEY=%USERPROFILE%\.ssh\id_rsa.pub
) else (
    set PUBKEY=
)

if defined PUBKEY (
    echo Found public key at %PUBKEY%. Uploading to %REMOTE_HOST%...
    for %%F in ("%PUBKEY%") do set PUBNAME=%%~nxF
    scp "%PUBKEY%" %REMOTE_HOST%:/root/!PUBNAME! || (
        echo Warning: scp failed. You may need to provide password or set up key auth manually.
    )
    echo Appending key on remote and cleaning up...
    ssh %REMOTE_HOST% "mkdir -p ~/.ssh && cat /root/!PUBNAME! >> ~/.ssh/authorized_keys && rm -f /root/!PUBNAME! && chmod 600 ~/.ssh/authorized_keys" || (
        echo Warning: remote key append may have failed.
    )
) else (
    echo No public key found locally; skipping upload.
)

echo Running remote update: cd telegram-file-transfer && pm2 flush && git pull && pm2 restart all
ssh %REMOTE_HOST% "cd /root/telegram-file-transfer && pm2 flush && git pull && pm2 restart all" || (
    echo ERROR: Remote update failed.
    exit /b 1
)

echo.
echo [6/6] Showing production logs...

ssh %REMOTE_HOST% "pm2 logs --lines 80 --nostream"
