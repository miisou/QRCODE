# Verification Service

Backend for GovVerify MVP.

## Setup

1.  Create virtual environment: `python3 -m venv venv`
2.  Activate: `source venv/bin/activate`
3.  Install dependencies: `pip install -r requirements.txt`

## running the server

Run the server:
```bash
./run.sh
```

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
