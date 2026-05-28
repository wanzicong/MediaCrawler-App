# Data-API-Service Dockerfile
# 数据 & 配置中心，无需浏览器依赖，使用轻量镜像

FROM python:3.11-slim

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv

# 利用 Docker 缓存：先复制依赖文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# 安装中文字体（词云生成需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# 复制代码
COPY . .

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
