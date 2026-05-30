@echo off
title Organic Chemistry App Launcher

echo ========================================
echo Organic Chemistry App を起動します
echo ========================================

echo.
echo [1/3] Backend を起動中...
start "Organic Backend" cmd /k "cd /d C:\Users\ishik\organic-app\backend && python -m uvicorn main:app --reload"

echo.
echo [2/3] Frontend を起動中...
start "Organic Frontend" cmd /k "cd /d C:\Users\ishik\organic-app\frontend && npm run dev"

echo.
echo [3/3] ブラウザを開きます...
timeout /t 6 /nobreak > nul

start http://localhost:3000

echo.
echo 起動処理が完了しました。
echo Backend と Frontend の黒い画面は閉じないでください。
pause