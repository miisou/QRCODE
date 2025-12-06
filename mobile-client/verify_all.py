import requests
from config import API_URL
import time

def test_scenario(url, expected_verdict):
    print(f"--- Testing URL: {url} ---")
    
    # 1. Init Session
    try:
        # Update: Send URL in headers, add User-Agent
        headers = {
            "X-Client-Url": url,
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        }
        # Body is now empty/ignored for URL
        init_resp = requests.post(f"{API_URL}/session/init", json={}, headers=headers)
        init_resp.raise_for_status()
        data = init_resp.json()
        nonce = data["nonce"]
        print(f"Session Initialized. Nonce: {nonce}")
    except Exception as e:
        print(f"Failed to init session: {e}")
        return

    # 2. Verify Token
    try:
        # Simulate mobile client delay
        time.sleep(1) 
        verify_resp = requests.post(f"{API_URL}/session/verify", json={"token": nonce})
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()
        
        verdict = verify_data["verdict"]
        print(f"Verification Verdict: {verdict}")
        
        if verdict == expected_verdict:
            print("✅ SUCCESS")
        else:
            print(f"❌ FAILED. Expected {expected_verdict}, got {verdict}")
            
    except Exception as e:
        print(f"Failed to verify: {e}")
        if verify_resp:
            print(verify_resp.text)

def main():
    print("Running Verification Suit...\n")
    test_scenario("https://gov.pl", "TRUSTED")
    test_scenario("https://podatki.gov.pl/zaloguj", "TRUSTED")
    test_scenario("https://evil.com/login", "UNSAFE")
    test_scenario("http://fake-gov.pl", "UNSAFE")
    test_scenario("http://localhost:5174/", "TRUSTED")
    print("\nDone.")

if __name__ == "__main__":
    main()
