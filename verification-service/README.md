# Verification Service

Backend service for Gov Verify. Built with FastAPI.

## Setup

1.  Create virtual environment: `python3 -m venv venv`
2.  Activate: `source venv/bin/activate`
3.  Install dependencies: `pip install -r requirements.txt`

## running the server

Run the server:
```bash
./run.sh
```

## Running with Docker

## Running with Docker

You can run the service using standard Docker Compose (v2):

```bash
docker compose up --build
```
Or simply use the helper script:
```bash
./start.sh
```

This will start the verification service on port 8001 (mapped to container 8000) and a Redis instance on port 6380.

To run only the verification service container:
```bash
docker build -t verification-service .
docker run -p 8000:8000 --env REDIS_HOST=host.docker.internal verification-service
```
(Note: `host.docker.internal` is used to access localhost from container on some systems; otherwise ensure Redis is accessible).

## Deployment

To deploy to Docker Hub, use the provided script:

```bash
./deploy.sh <YOUR_DOCKER_HUB_USERNAME>
```

This script will:
1. Build the image.
2. Run it locally to verify it starts and responds to `/docs`.
3. Push it to Docker Hub under your username.

## Running Tests

The service includes integration tests using `badssl.com` to verify SSL logic.

```bash
# Install test dependencies
pip install pytest

# Run tests (ensure PYTHONPATH is set)
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 -m pytest tests/test_ssl.py
```
Server runs on `http://localhost:8000`.

## Stopping

Press `Ctrl+C` in the terminal where it's running.
