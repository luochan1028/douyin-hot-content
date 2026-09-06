#!/bin/bash
# 抖音热点内容自动生成与发布系统 - Linux 启动脚本
# 用法: bash start.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 优先使用项目虚拟环境
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
    PYTHON=python
elif command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "错误: 未找到 Python3，请先运行 bash deploy.sh"
    exit 1
fi

echo "=================================================="
echo "  抖音热点内容自动生成与发布系统"
echo "=================================================="
echo "  [1] 运行一次完整流程（抓取→生成→发布）"
echo "  [2] 仅抓取热点"
echo "  [3] 启动 Web 管理后台"
echo "  [4] 启动定时调度（持续运行）"
echo "  [5] 运行端到端测试"
echo "  [6] 初始化/重置数据库"
echo "  [7] 抖音扫码登录"
echo "  [8] 检查抖音登录状态"
echo "  [0] 退出"
echo "=================================================="
read -p "请选择操作: " choice

case "$choice" in
    1) echo "[执行] 完整流程..."; $PYTHON -m app pipeline ;;
    2) echo "[执行] 仅抓取热点..."; $PYTHON -m app crawl ;;
    3) echo "[启动] Web 管理后台 http://0.0.0.0:8000"; $PYTHON -m app web ;;
    4) echo "[启动] 定时调度..."; $PYTHON -m app scheduler ;;
    5) echo "[执行] 端到端测试..."; $PYTHON e2e_test.py ;;
    6) echo "[执行] 初始化数据库..."; $PYTHON -m app init-db ;;
    7) echo "[执行] 抖音扫码登录（headless）..."; $PYTHON -m app login --headless ;;
    8) echo "[执行] 检查登录状态..."; $PYTHON -m app login-status ;;
    0) echo "再见！" ;;
    *) echo "无效选择" ;;
esac
