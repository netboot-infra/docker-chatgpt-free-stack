# 1. Sử dụng Image chính chủ của Playwright (Đã bao gồm Python, Chromium và Dependencies hệ thống)
# Chọn phiên bản jammy (Ubuntu 22.04) để ổn định nhất
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 2. Copy và cài đặt thư viện Python (Flask, etc...)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Cài đặt trình duyệt Chromium (Để đảm bảo version khớp 100%)
RUN playwright install chromium

# 4. Copy toàn bộ code của bạn vào
COPY . .

# 5. Thiết lập biến môi trường
ENV HEADLESS_MODE=True
ENV PYTHONUNBUFFERED=1

# 6. Mở port
EXPOSE 5001

# 7. Chạy ứng dụng
CMD ["python", "apigpt.py"]

