import requests
import time
import sys

# Default URL
BASE_URL = "http://localhost:8000/api/v1"

def test_rate_limit():
    print("Testing Rate Limit on /session/init (Limit: 20 per min)")
    print(f"Target: {BASE_URL}")
    
    url = f"{BASE_URL}/session/init"
    headers = {"X-Client-Url": "https://gov.pl"}
    payload = {"url": "https://gov.pl"}
    
    # 1. Send 20 requests (Allowed)
    print("Sending 20 allowed requests...")
    for i in range(20):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            status = response.status_code
            if status not in [200, 201]:
                print(f"❌ Failed early at req {i+1}: Status {status}")
                print(response.text)
                return
            # Optional: small delay to not bombard too hard if system is slow, 
            # but rate limit is per minute so fast is fine.
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return
            
    print("✅ 20 requests passed.")

    # 2. Send 21st request (Should be 429)
    print("Sending 21st request (Expect 429)...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 429:
            print("✅ SUCCESS: Rate Limiting Active (Got 429).")
        else:
            print(f"❌ FAILED: Exprected 429, got {response.status_code}")
            print("Note: If you ran other tests recently, the counter might be different, or Redis might be flushed.")
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    test_rate_limit()
