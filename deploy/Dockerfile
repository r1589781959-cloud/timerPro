# 使用轻量级 Python 镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件并安装
COPY web_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个 Web 目录
COPY web_app/ ./web_app/

# 暴露端口
EXPOSE 8000

# 运行命令 (使用 SaaS 版本)
CMD ["uvicorn", "web_app.main_saas:app", "--host", "0.0.0.0", "--port", "8000"]
