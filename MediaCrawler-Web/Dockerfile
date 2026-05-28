# MediaCrawler-Web Dockerfile
# 多阶段构建：Node 编译 + Nginx 静态服务 + API 反向代理

# ============ 构建阶段 ============
FROM node:18-alpine AS build

WORKDIR /app

# 安装依赖（使用 npm，避免 workspace 上下文问题）
COPY package.json ./
RUN npm install --legacy-peer-deps

# 复制源码并构建
COPY . .
RUN npx vite build

# ============ 运行阶段 ============
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
