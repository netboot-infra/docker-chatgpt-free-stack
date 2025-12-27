# Use the official Playwright image (includes Python, Chromium, and system dependencies)
# Choose the Jammy version (Ubuntu 22.04) for maximum stability
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Update system packages and install Xvfb
RUN apt update && apt install -y xvfb

# Copy and install Python libraries (Flask, etc.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium browser (ensures exact version match)
RUN playwright install chromium

# Copy the entire application code
COPY . .

# Set environment variables
ENV HEADLESS_MODE=True
ENV PYTHONUNBUFFERED=1

# Expose application port
EXPOSE 5001

# Run the application
CMD ["python", "apigpt.py"]
