# Mobile Client Simulator

Python script to simulate the Mobile App behavior for Gov Verify.
 mobile app.

## Setup

1.  Create venv: `python3 -m venv venv`
2.  Activate: `source venv/bin/activate`
3.  Install deps: `pip install -r requirements.txt`

## Running the Simulator

To simulate scanning a QR code:
```bash
python client.py <TOKEN_FROM_WEB_CLIENT>
```

## Automated Tests

### 1. Functional Verification Suite (verify_all.py)
Tests the full verification flow against various scenarios (Good, Phishing, Bad SSL, Tar Recursion).
```bash
python verify_all.py
```

### 2. Rate Limiting Stress Test (test_rate_limit.py)
Tests the Redis-backed rate limiter (20 requests/minute).
**Note:** Run this separately from `verify_all.py` to avoid shared quota conflicts.
```bash
python test_rate_limit.py
```

Run automated verification suite:
```bash
./venv/bin/python verify_all.py
```

## Stopping

The scripts exit automatically after execution.
