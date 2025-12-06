# Mobile Client Simulator

Simulator for GovVerify MVP mobile app.

## Setup

1.  Create venv: `python3 -m venv venv`
2.  Activate: `source venv/bin/activate`
3.  Install deps: `pip install -r requirements.txt`

## Running

Verify a specific token:
```bash
./venv/bin/python client.py <TOKEN>
```

Run automated verification suite:
```bash
./venv/bin/python verify_all.py
```

## Stopping

The scripts exit automatically after execution.
