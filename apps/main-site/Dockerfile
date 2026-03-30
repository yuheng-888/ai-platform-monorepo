FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git curl wget unzip libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js（Vite 8 需要 Node 20.19+）
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app/

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装浏览器运行依赖并预抓取 Camoufox，避免 solver 启动时缺少系统库或版本信息
RUN python -m playwright install --with-deps chromium && \
    python -m camoufox fetch

# 构建前端
WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app/embedded/gemini_business2api/frontend
RUN npm install && npm run build

WORKDIR /app

EXPOSE 8000 8889

CMD ["python", "main.py"]
