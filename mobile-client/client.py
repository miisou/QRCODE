import requests
import sys
from config import API_URL

def verify_token(token):
    print(f"Connecting to {API_URL}...")
    try:
        response = requests.post(f"{API_URL}/session/verify", json={"token": token})
        if response.status_code == 200:
            data = response.json()
            print("\n==============================")
            print(f"VERIFICATION RESULT: {data['verdict']}")
            print(f"Trust Score: {data.get('trust_score')}/100")
            print(f"URL: {data.get('checked_url')}")
            
            if data['verdict'] == "TRUSTED":
                print("✅ The website is SAFE and OFFICIAL.")
            elif data['verdict'] == "CAUTION":
                print("⚠️  The website is trusted but has warnings.")
            else:
                print("❌ WARNING: The website is UNSAFE! Do not enter data.")

            print("\n--- Technical Details ---")
            print(f"Client IP: {data.get('client_ip')}")
            print(f"User Agent: {data.get('user_agent')}")
            print(f"Device: {data.get('device_brand')} {data.get('device_os')} {data.get('device_browser')}")
            
            logs = data.get('logs', [])
            if logs:
                 print("\n--- Verification Logs ---")
                 for log in logs:
                     prefix = "[FAIL]" if "FAIL" in log or "NOT" in log else "[PASS]"
                     if "FAIL" in prefix: 
                        print(f"❌ {log}")
                     else:
                        print(f"✅ {log}")

            print("==============================\n")
        elif response.status_code == 404:
            print("\nError: Session not found (Invalid Token).")
        elif response.status_code == 409:
            print("\nError: Session already consumed (Replay Attack?).")
        elif response.status_code == 410:
             print("\nError: Session expired.")
        else:
            print(f"\nError: Server returned {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"\nConnection Error: {e}")

if __name__ == "__main__":
    print("GovVerify Mobile Client Simulator")
    print("---------------------------------")
    if len(sys.argv) > 1:
        token = sys.argv[1]
    else:
        token = input("Please enter the token from QR: ").strip()
    
    if token:
        verify_token(token)
    else:
        print("No token provided.")
