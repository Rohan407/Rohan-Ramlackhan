FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    unzip \
    xvfb \
    chromium \
    chromium-driver \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for browser automation
RUN pip install --no-cache-dir playwright
RUN playwright install chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Set Chrome path for Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_PATH=/usr/bin/chromium

# Expose ports
EXPOSE 8501 8000

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Start the dashboard in background\n\
streamlit run api/dashboard.py --server.port=8501 --server.address=0.0.0.0 &\n\
\n\
# Start the main orchestrator\n\
python -m workflows.main_orchestrator\n\
' > /app/start.sh

RUN chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/ || exit 1

# Default command
CMD ["/app/start.sh"]