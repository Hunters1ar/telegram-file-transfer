@echo off
setlocal EnableDelayedExpansion

echo.
echo [1/5] Building website locally...

cd website
call npm run build

if errorlevel 1 (
    echo ERROR: Website build failed.
    exit /b 1
)

cd ..

echo.
echo [2/5] Committing changes...

git add .
git commit -m "Fix Telegram web app deployment"

if errorlevel 1 (
    echo ERROR: Git commit failed.
    exit /b 1
)

git config --local credential.username Hunters1ar

echo.
echo [3/5] Pushing changes...

git push

if errorlevel 1 (
    echo ERROR: Git push failed.
    exit /b 1
)

echo.
echo [4/5] Updating production server...

ssh root@134.209.75.49 "pm2 flush && cd /root/telegram-file-transfer && git pull && cd website && npm ci && npm run build && cd .. && pm2 restart all"

if errorlevel 1 (
    echo ERROR: Server deployment failed.
    exit /b 1
)

echo.
echo [5/5] Showing production logs...

ssh root@134.209.75.49 "pm2 logs --lines 80 --nostream"
