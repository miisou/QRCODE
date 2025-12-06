# Mobile Client Simulator

Simulator for GovVerify MVP mobile app.

## Setup

1.  Create venv: `python3 -m venv venv`
2.  Activate: `source venv/bin/activate`
3.  Install deps: `pip install -r requirements.txt`

## Running the Simulator

To simulate scanning a QR code:
```bash
python client.py <TOKEN_FROM_WEB_CLIENT>
```

## Running Automated Tests

You can run the full suite of verification scenarios using the `verify_all.py` script.
Ensure the Backend (`verification-service`) is running first.

```bash
python verify_all.py
```

Run automated verification suite:
```bash
./venv/bin/python verify_all.py
```

## Stopping

The scripts exit automatically after execution.
