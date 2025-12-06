#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting server..."
# Check if running inside app folder or root, main.py is in app/main.py? 
# Wait, main.py is in verification-service/app/main.py.
# But inside main.py we do `import uvicorn; uvicorn.run("main:app")`.
# If we run from verification-service root, we should run `uvicorn app.main:app`.
# The file I wrote for main.py assumes checking `__name__ == "__main__"`.
# Let's adjust command to run module or file.
# Better to run `uvicorn app.main:app` from verification-service root.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
