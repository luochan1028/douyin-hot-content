# 抖音热点内容自动生成与发布系统 - Dockerfile
# 基于 python:3.11-slim，集成 FFmpeg、中文字体、Playwright Chromium
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# 安装系统依赖：FFmpeg、中文字体、编译工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright Chromium 浏览器
RUN playwright install chromium

# 复制应用代码
COPY . .

# 数据目录权限
RUN mkdir -p /app/storage/images /app/storage/videos /app/storage/cookies /app/storage/logs

# 暴露 Web 端口
EXPOSE 8000

# 启动命令：初始化数据库 + 启动 Web 服务
CMD ["sh", "-c", "python -m app init-db && python -m app web"]
