#!/bin/bash
set -e

# Start Redis in background
echo "Starting Redis server..."
redis-server --daemonize yes --bind 127.0.0.1

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
until redis-cli ping 2>/dev/null; do
    sleep 1
done
echo "Redis is ready!"

# Start the application
echo "Starting verification service..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
