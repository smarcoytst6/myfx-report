# Dockerfile（生產版）
FROM python:3.12-slim

# 安裝 matplotlib 所需的系統庫
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY app.py .

EXPOSE 8000

# 啟動 Gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "300", "app:app"]