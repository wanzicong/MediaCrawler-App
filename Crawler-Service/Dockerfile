# Crawler-Service Dockerfile
# 基于 Python 3.11 + Playwright + Google Chrome（CDP 反检测）

FROM python:3.11-slim

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv

# 安装系统依赖：Playwright 浏览器 + Chrome + 中文字体 + C 编译器
RUN apt-get update && apt-get install -y --no-install-recommends \
    # C 编译器（cffi 等需要从源码编译）
    build-essential \
    # Playwright 浏览器依赖
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 \
    libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 libu2f-udev \
    libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2 \
    xdg-utils \
    # Chrome 安装工具
    wget gnupg ca-certificates \
    # 中文字体（词云生成）
    fonts-wqy-zenhei fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 安装 Google Chrome Stable（CDP 模式需要真实 Chrome）
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | \
    gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
    http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# 利用 Docker 缓存：先复制依赖文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# 复制代码
COPY . .

# PYTHONPATH 确保主脚本的模块导入正确
ENV PYTHONPATH=.

EXPOSE 8081

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8081"]
