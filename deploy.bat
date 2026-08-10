@echo off
setlocal EnableDelayedExpansion

cd website

for /f "tokens=2 delims='" %%A in ('findstr /C:"const CACHE_NAME" sw.js') do set "CURRENT=%%A"

for /f "tokens=1,2 delims=." %%A in ("!CURRENT:hunterstar-v=!") do (
    set "MAJOR=%%A"
    set "MINOR=%%B"
)

if "!MINOR!"=="" (
    set "NEW=hunterstar-v!MAJOR!.1"
) else if "!MINOR!"=="9" (
    set /a MAJOR+=1
    set "NEW=hunterstar-v!MAJOR!"
) else (
    set /a MINOR+=1
    set "NEW=hunterstar-v!MAJOR!.!MINOR!"
)

powershell -Command "(Get-Content sw.js -Raw) -replace 'const CACHE_NAME = ''[^'']+''', 'const CACHE_NAME = ''!NEW!''' | Set-Content sw.js -Encoding UTF8"

echo.
echo Cache version: !CURRENT! -^> !NEW!
echo.

cd ..

git add .
git commit -m "f"
git push

ssh root@134.209.75.49 "cd /root/telegram-file-transfer && pm2 flush all && git pull && pm2 restart all"

cd website
vercel --prod

endlocal