# Gov Verify MVP

A Minimum Viable Product for a government domain verification system. This project consists of three main components working together to demonstrate a secure verification flow.

## 📂 Project Structure

- **[verification-service](./verification-service)**: The backend service built with Python and FastAPI. It handles verification logic and serves as the source of truth.
- **[web-client](./web-client)**: The frontend web application built with React and Vite. It provides the user interface for the verification process.
- **[mobile-client](./mobile-client)**: A Python-based simulator for the mobile app client. It simulates the device that scans QR codes and communicates with the backend.

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+
- Node.js 16+ & npm

### 1. Verification Service (Backend)

The backend needs to be running first.

```bash
cd verification-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
./run.sh
```
> The service will start on `http://localhost:8000`.

### 2. Web Client (Frontend)

Open a new terminal for the frontend.

```bash
cd web-client
npm install
npm run dev
```
> The web app will start on `http://localhost:5173`.

### 3. Mobile Client Simulator

Use the simulator to test the verification flow. Open a third terminal.

```bash
cd mobile-client
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**To verify a token:**
```bash
./venv/bin/python client.py <TOKEN_FROM_QR_CODE>
```

**To run the automated verification suite:**
```bash
./venv/bin/python verify_all.py
```

## 📖 Documentation

For detailed instructions on each component, please refer to their respective READMEs:
- [Verification Service README](./verification-service/README.md)
- [Web Client README](./web-client/README.md)
- [Mobile Client README](./mobile-client/README.md)