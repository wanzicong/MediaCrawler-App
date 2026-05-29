FROM python:3.12-slim

WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-dotenv httpx

# 复制代码
COPY . .

EXPOSE 8082

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8082"]
