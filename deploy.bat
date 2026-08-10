@echo off
setlocal EnableDelayedExpansion

echo.

echo [1/6] Updating service worker version...

python bump_version.py

if errorlevel 1 (
    echo.
    echo DEPLOYMENT STOPPED: Service worker version update failed.
    exit /b 1
)

echo.

echo [2/6] Current service worker version:

findstr /C:"const CACHE_NAME" website\sw.js

if errorlevel 1 (
    echo ERROR: Could not read CACHE_NAME.
    exit /b 1
)

echo.

echo [2/6] Deploying website to Vercel...

cd website

call vercel --prod

if errorlevel 1 (
    echo ERROR: Vercel deployment failed.
    exit /b 1
)

cd ..

echo.

echo [4/6] Committing changes...

git add .
git commit -m "f"

if errorlevel 1 (
    echo ERROR: Git commit failed.
    exit /b 1
)

git config --local credential.username Hunters1ar

git push

if errorlevel 1 (
    echo ERROR: Git push failed.
    exit /b 1
)

echo.


echo [5/6] Updating production server...

ssh root@134.209.75.49 " pm2 flush && cd /root/telegram-file-transfer && git pull && pm2 restart all"

if errorlevel 1 (
    echo ERROR: Server deployment failed.
    exit /b 1
)
echo.


cls

ssh root@134.209.75.49 "pm2 logs 10"                                                                  