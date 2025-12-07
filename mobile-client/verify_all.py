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

def test_ble_scenario(url, expected_verdict, ble_proximity_mode):
    """
    Test BLE proximity verification scenarios.
    ble_proximity_mode: 'confirmed', 'not_supported', 'not_confirmed', or None
    """
    print(f"--- Testing URL: {url} (BLE: {ble_proximity_mode}) ---")
    
    # 1. Init Session
    try:
        headers = {
            "X-Client-Url": url,
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        }
        init_resp = requests.post(f"{API_URL}/session/init", json={}, headers=headers)
        init_resp.raise_for_status()
        data = init_resp.json()
        nonce = data["nonce"]
        print(f"Session Initialized. Nonce: {nonce}")
    except Exception as e:
        print(f"Failed to init session: {e}")
        return

    # 2. Send BLE Proximity Confirmation (if applicable)
    if ble_proximity_mode:
        try:
            proximity_payload = {
                "ble_uuid": "test-uuid-" + nonce[:8],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            if ble_proximity_mode == "confirmed":
                # Simulate successful BLE proximity detection
                proximity_payload["found"] = True
                proximity_payload["supported"] = True
                print(f"  → Sending BLE proximity: CONFIRMED")
            elif ble_proximity_mode == "not_supported":
                # Simulate BLE not supported by browser
                proximity_payload["found"] = True
                proximity_payload["supported"] = False
                print(f"  → Sending BLE proximity: NOT SUPPORTED")
            elif ble_proximity_mode == "not_confirmed":
                # Simulate BLE supported but phone not found
                # Web client NOW sends proximity data with supported=true
                proximity_payload["found"] = False
                proximity_payload["supported"] = True  # BLE IS supported
                print(f"  → Sending BLE proximity: SUPPORTED but phone NOT FOUND")
            
            if proximity_payload:
                prox_resp = requests.post(
                    f"{API_URL}/session/proximity/{nonce}",
                    json=proximity_payload
                )
                prox_resp.raise_for_status()
                
        except Exception as e:
            print(f"  → Failed to send proximity: {e}")

    # 3. Verify Token
    try:
        time.sleep(1)
        verify_resp = requests.post(f"{API_URL}/session/verify", json={"token": nonce})
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()
        
        verdict = verify_data["verdict"]
        print(f"Verification Verdict: {verdict}")
        
        # Show BLE-related logs
        if "logs" in verify_data:
            ble_logs = [log for log in verify_data["logs"] if "BLE" in log or "proximity" in log.lower()]
            if ble_logs:
                print(f"  BLE Logs: {ble_logs}")
        
        if verdict == expected_verdict:
            print("✅ SUCCESS")
        else:
            print(f"❌ FAILED. Expected {expected_verdict}, got {verdict}")
            
    except Exception as e:
        print(f"Failed to verify: {e}")
        if verify_resp:
            print(verify_resp.text)

def main():
    print("Running Verification Suite...\n")
    
    print("=== STANDARD TESTS (No BLE) ===")
    test_scenario("https://gov.pl", "TRUSTED")
    test_scenario("https://podatki.gov.pl/zaloguj", "TRUSTED")
    test_scenario("https://evil.com/login", "UNSAFE")
    test_scenario("http://fake-gov.pl", "UNSAFE")
    test_scenario("http://localhost:5174/", "UNSAFE")
    
    print("\n=== SSL SCENARIOS (badssl.com) ===")
    test_scenario("https://sha256.badssl.com/", "TRUSTED")
    test_scenario("https://expired.badssl.com/", "UNSAFE")
    test_scenario("https://wrong.host.badssl.com/", "UNSAFE")
    test_scenario("https://revoked.badssl.com/", "UNSAFE")
    
    print("\n=== BLE PROXIMITY TESTS ===")
    test_ble_scenario("https://gov.pl", "TRUSTED", "confirmed")    
    test_ble_scenario("https://gov.pl", "TRUSTED", "not_supported")    
    test_ble_scenario("https://gov.pl", "UNSAFE", "not_confirmed")
    test_ble_scenario("https://expired.badssl.com/", "UNSAFE", "confirmed")
    
    print("\n=== ALL TESTS COMPLETE ===")

if __name__ == "__main__":
    main()
