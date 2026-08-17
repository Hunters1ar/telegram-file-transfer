
@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem HUNTERSTAR DEPLOY SCRIPT
rem Usage:
rem   deploy.bat
rem   deploy.bat --force
rem ============================================================

set "FORCE=0"
if /I "%~1"=="--force" set "FORCE=1"

set "REMOTE_HOST=root@134.209.75.49"
set "REMOTE_DIR=/root/telegram-file-transfer"

echo.
echo ============================================================
echo                  HUNTERSTAR DEPLOY
echo ============================================================
echo.

rem ============================================================
rem [0/6] PRE-FLIGHT CHECKS
rem ============================================================

echo [0/6] Pre-flight checks...
echo.

where ssh >nul 2>&1
if errorlevel 1 (
    echo ERROR: ssh not found in PATH.
    echo Install/enable the Windows OpenSSH Client.
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERROR: npm not found in PATH.
    echo Install Node.js/npm.
    exit /b 1
)

where git >nul 2>&1
if errorlevel 1 (
    echo ERROR: git not found in PATH.
    exit /b 1
)

where vercel >nul 2>&1
if errorlevel 1 (
    echo ERROR: Vercel CLI not found in PATH.
    echo Install it with:
    echo npm install -g vercel
    exit /b 1
)

rem ============================================================
rem GIT CLEAN CHECK
rem ============================================================

if "%FORCE%"=="0" (
    echo Checking Git working tree...

    git status --porcelain > "%TEMP%\hunterstar_git_status.txt"

    for %%A in ("%TEMP%\hunterstar_git_status.txt") do (
        if %%~zA GTR 0 (
            echo.
            echo ERROR: Git working tree is not clean.
            echo.
            git status --short
            echo.
            echo Commit/stash your changes first.
            echo Or bypass this check with:
            echo.
            echo     deploy.bat --force
            echo.
            del "%TEMP%\hunterstar_git_status.txt" >nul 2>&1
            exit /b 1
        )
    )

    del "%TEMP%\hunterstar_git_status.txt" >nul 2>&1
) else (
    echo WARNING: --force enabled.
    echo Skipping Git clean check.
)

echo.
echo [0/6] Pre-flight checks passed.
echo.

rem ============================================================
rem [1/6] BUILD WEBSITE
rem ============================================================

echo [1/6] Preparing website (vanilla HTML)...
echo.

if not exist "website" (
    echo ERROR: website directory not found.
    exit /b 1
)

echo Website is static. Skipping build step.
echo.

rem ============================================================
rem [2/6] PREPARE GIT
rem ============================================================

echo [2/6] Preparing Git push...
echo.

for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD') do (
    set "BRANCH=%%B"
)

if not defined BRANCH (
    echo ERROR: Could not determine current Git branch.
    exit /b 1
)

echo Current branch: !BRANCH!

git config --local credential.username Hunters1ar >nul 2>&1

echo.

rem ============================================================
rem [3/6] PUSH TO GITHUB
rem ============================================================

echo [3/6] Pushing changes to remote...
echo.

git push origin "!BRANCH!"
if errorlevel 1 (
    echo.
    echo ERROR: Git push failed.
    echo Check your Git credentials, remote, and network connection.
    exit /b 1
)

echo.
echo Git push successful.
echo.

rem ============================================================
rem [4/6] DEPLOY WEBSITE TO VERCEL
rem ============================================================

echo [4/6] Deploying website to Vercel...
echo.

if defined VERCEL_TOKEN (
    echo Using VERCEL_TOKEN for non-interactive deployment...

    vercel --prod --token "!VERCEL_TOKEN!" --confirm

    if errorlevel 1 (
        echo ERROR: Vercel deployment failed.
        exit /b 1
    )
) else (
    echo VERCEL_TOKEN is not set.
    echo Running interactive Vercel deployment...

    vercel --prod --confirm

    if errorlevel 1 (
        echo ERROR: Vercel deployment failed.
        exit /b 1
    )
)

echo.
echo Vercel deployment successful.
echo.

rem ============================================================
rem [5/6] UPDATE VPS
rem ============================================================

echo [5/6] Updating backend on VPS...
echo.
echo Remote server: %REMOTE_HOST%
echo Remote directory: %REMOTE_DIR%
echo.

rem ------------------------------------------------------------
rem Find SSH public key
rem ------------------------------------------------------------

set "PUBKEY="

if exist ".ssh\deploy_id_rsa.pub" (
    set "PUBKEY=.ssh\deploy_id_rsa.pub"
) else if exist "%USERPROFILE%\.ssh\id_rsa.pub" (
    set "PUBKEY=%USERPROFILE%\.ssh\id_rsa.pub"
) else if exist "%USERPROFILE%\.ssh\id_ed25519.pub" (
    set "PUBKEY=%USERPROFILE%\.ssh\id_ed25519.pub"
)

if defined PUBKEY (
    echo Found SSH public key:
    echo !PUBKEY!
    echo.

    for %%F in ("!PUBKEY!") do (
        set "PUBNAME=%%~nxF"
    )

    echo Uploading SSH public key...

    scp "!PUBKEY!" "%REMOTE_HOST%:/root/!PUBNAME!"

    if errorlevel 1 (
        echo WARNING: Failed to upload SSH public key.
        echo Continuing with existing SSH authentication...
    ) else (
        echo SSH key uploaded.
        echo Adding key to authorized_keys...

        ssh "%REMOTE_HOST%" "mkdir -p ~/.ssh && touch ~/.ssh/authorized_keys && grep -qxF -f /root/!PUBNAME! ~/.ssh/authorized_keys || cat /root/!PUBNAME! >> ~/.ssh/authorized_keys && rm -f /root/!PUBNAME! && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"

        if errorlevel 1 (
            echo WARNING: Failed to update authorized_keys.
        ) else (
            echo SSH key successfully configured.
        )
    )
) else (
    echo No SSH public key found locally.
    echo Skipping SSH key upload.
)

echo.
echo Updating backend...

ssh "%REMOTE_HOST%" "cd %REMOTE_DIR% && git pull && pm2 flush && pm2 restart all"

if errorlevel 1 (
    echo.
    echo ERROR: Remote update failed.
    exit /b 1
)

echo.
echo Backend update successful.
echo.

rem ============================================================
rem [6/6] PRODUCTION LOGS
rem ============================================================

echo [6/6] Showing production logs...
echo.
echo ============================================================
echo                    PM2 LOGS
echo ============================================================
echo.

ssh "%REMOTE_HOST%" "pm2 logs --lines 80 --nostream"

echo.
echo ============================================================
echo                  DEPLOY COMPLETE
echo ============================================================
echo.

exit /b 0
 
