FROM python:3.9-slim

WORKDIR /app

# 安裝系統層級依賴 (OpenCV 需要)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 預設指令在 docker-compose 中定義，這裡留空或作為備援
CMD ["celery", "-A", "tasks", "worker", "--loglevel=info"]

