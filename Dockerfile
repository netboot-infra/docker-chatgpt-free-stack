# Stage 1: Build dependencies
FROM python:3.9-slim AS builder

WORKDIR /app

# Cài các thư viện cần thiết tối thiểu để chạy Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxrandr2 libxdamage1 libpango-1.0-0 \
    libgbm1 libasound2 libxshmfence1 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements và cài đặt Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

# Copy code
COPY . .

# Stage 2: Chạy thực tế (production) — image cực nhẹ
FROM python:3.9-slim

WORKDIR /app

# Copy từ builder stage sang
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

# Expose port
EXPOSE 5001

# Lệnh chạy app
CMD ["python", "apigpt.py"]
