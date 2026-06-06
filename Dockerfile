FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

# 暴露 8000 端口
EXPOSE 8000

# 默认运行 gunicorn viewflow_demo.wsgi
CMD ["gunicorn", "viewflow_demo.wsgi", "--bind", "0.0.0.0:8000"]
