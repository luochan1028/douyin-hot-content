#!/bin/bash
# ==================================================
# 抖音热点内容自动生成与发布系统 - Linux 云主机一键部署
# 支持: Ubuntu 20.04+ / Debian 11+ / CentOS 7+
# 用法: bash deploy.sh
# ==================================================

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

echo "=========================================="
echo "  抖音热点系统 - Linux 云主机部署"
echo "=========================================="

# 检测包管理器
if command -v apt-get &> /dev/null; then
    PKG="apt-get"
elif command -v yum &> /dev/null; then
    PKG="yum"
else
    echo "错误: 不支持的包管理器，请手动安装依赖"
    exit 1
fi

echo "[1/6] 安装系统依赖 (Python3, venv, FFmpeg, 中文字体)..."
if [ "$PKG" = "apt-get" ]; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip ffmpeg fonts-wqy-zenhei fonts-wqy-microhei
else
    sudo yum install -y python3 python3-virtualenv ffmpeg wqy-zenhei-fonts wqy-microhei-fonts
fi

echo "[2/6] 创建 Python 虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "虚拟环境已创建: $VENV_DIR"
else
    echo "虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
source "$VENV_DIR/bin/activate"

echo "[3/6] 安装 Python 依赖 (虚拟环境内)..."
pip install --upgrade pip
pip install -r requirements.txt

echo "[4/6] 安装 Playwright Chromium..."
python -m playwright install chromium
# Playwright 运行依赖（Debian/Ubuntu）
if [ "$PKG" = "apt-get" ]; then
    python -m playwright install-deps chromium
fi

echo "[5/6] 初始化数据库..."
python -m app init-db

echo "[6/6] 配置 .env..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "已生成 .env，请按需修改配置（账号定位、通知渠道等）"
else
    echo ".env 已存在，跳过"
fi

echo ""
echo "=========================================="
echo "  部署完成！"
echo "=========================================="
echo "  虚拟环境已激活，可直接运行："
echo "    python -m app web        # Web 管理后台"
echo "    python -m app pipeline   # 完整流水线"
echo "    python -m app scheduler  # 定时调度"
echo "    python -m app health     # 健康检查"
echo ""
echo "  重新登录后需先激活虚拟环境："
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "  一键启动菜单: bash start.sh"
echo "=========================================="
