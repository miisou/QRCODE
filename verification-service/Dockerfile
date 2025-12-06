# Dockerfile for Verification Service

FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Redis and dependencies
RUN apt-get update && apt-get install -y redis-server && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy and set executable startup script
COPY docker-start.sh /docker-start.sh
RUN chmod +x /docker-start.sh

# Expose port
EXPOSE 8000

# Use startup script that runs both Redis and app
CMD ["/docker-start.sh"]
