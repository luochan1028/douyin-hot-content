@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ========== 抖音热点内容自动生成与发布系统 - 本地启动脚本 ==========
cd /d "%~dp0"

REM 设置环境变量
set PYTHON=%~dp0python311\python.exe
set FFMPEG_PATH=%~dp0ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe
set FFPROBE_PATH=%~dp0ffmpeg\ffmpeg-9.0.1-essentials_build\bin\ffprobe.exe
set PLAYWRIGHT_BROWSERS_PATH=%~dp0pw-browsers

:menu
cls
echo ==================================================
echo   抖音热点内容自动生成与发布系统
echo ==================================================
echo   [1] 运行一次完整流程（抓取→生成→发布）
echo   [2] 仅抓取热点
echo   [3] 启动 Web 管理后台
echo   [4] 启动定时调度（持续运行）
echo   [5] 运行端到端测试
echo   [6] 初始化/重置数据库
echo   [7] 抖音扫码登录
echo   [8] 检查抖音登录状态
echo   [0] 退出
echo ==================================================
set /p choice=请选择操作: 

if "%choice%"=="1" goto run_pipeline
if "%choice%"=="2" goto crawl
if "%choice%"=="3" goto web
if "%choice%"=="4" goto scheduler
if "%choice%"=="5" goto e2e
if "%choice%"=="6" goto init_db
if "%choice%"=="7" goto login
if "%choice%"=="8" goto login_status
if "%choice%"=="0" goto end
echo 无效选择，请重试
pause
goto menu

:run_pipeline
echo.
echo [执行] 完整流程...
"%PYTHON%" -m app pipeline
pause
goto menu

:crawl
echo.
echo [执行] 仅抓取热点...
"%PYTHON%" -m app crawl
pause
goto menu

:web
echo.
echo [启动] Web 管理后台 http://localhost:8000
echo 按 Ctrl+C 停止
"%PYTHON%" -m app web
pause
goto menu

:scheduler
echo.
echo [启动] 定时调度（高峰5分钟/低峰30分钟）
echo 按 Ctrl+C 停止
"%PYTHON%" -m app scheduler
pause
goto menu

:e2e
echo.
echo [执行] 端到端测试...
"%PYTHON%" e2e_test.py
pause
goto menu

:init_db
echo.
echo [执行] 初始化数据库...
"%PYTHON%" -m app init-db
echo 数据库初始化完成
pause
goto menu

:login
echo.
echo [执行] 抖音扫码登录...
"%PYTHON%" -m app login --no-headless
pause
goto menu

:login_status
echo.
echo [执行] 检查抖音登录状态...
"%PYTHON%" -m app login-status
pause
goto menu

:end
echo 再见！
endlocal
