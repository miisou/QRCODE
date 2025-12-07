import requests
from config import API_URL
import time
import websocket
import json
import threading
import ssl

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

def test_websocket_verification_success(url):
    """
    Test WebSocket notification when verification succeeds after proximity confirmation.
    """
    print(f"--- Testing WebSocket: {url} (Success Scenario) ---")
    
    # Convert API_URL to WebSocket URL
    ws_url = API_URL.replace("https://", "wss://").replace("http://", "ws://")
    
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
        return False
    
    # 2. Send BLE Proximity Confirmation (confirmed) - FIRST, before WebSocket
    try:
        proximity_payload = {
            "ble_uuid": "test-uuid-" + nonce[:8],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "found": True,
            "supported": True
        }
        prox_resp = requests.post(
            f"{API_URL}/session/proximity/{nonce}",
            json=proximity_payload
        )
        prox_resp.raise_for_status()
        print(f"  → BLE proximity confirmed")
    except Exception as e:
        print(f"  → Failed to send proximity: {e}")
        return False
    
    # 3. NOW connect WebSocket (right after proximity confirmation)
    ws_message_received = threading.Event()
    ws_message_data = None
    ws_error = None
    connection_established = threading.Event()
    ws = None
    ws_thread = None
    
    def on_message(ws, message):
        nonlocal ws_message_data
        try:
            ws_message_data = json.loads(message)
            print(f"  → WebSocket message received: {ws_message_data.get('type', 'unknown')}")
            ws_message_received.set()
        except Exception as e:
            print(f"  → Error parsing WebSocket message: {e}")
    
    def on_error(ws, error):
        nonlocal ws_error
        ws_error = error
        print(f"  → WebSocket error: {error}")
        connection_established.set()  # Signal that connection attempt finished (failed)
    
    def on_close(ws, close_status_code, close_msg):
        print(f"  → WebSocket closed: {close_status_code}")
    
    def on_open(ws):
        print(f"  → WebSocket connected")
        connection_established.set()  # Signal that connection is established
        # Send ping to keep connection alive
        try:
            ws.send("ping")
        except:
            pass
    
    # Connect to WebSocket
    ws_endpoint = f"{ws_url}/ws/verification/{nonce}"
    print(f"Connecting to WebSocket: {ws_endpoint}")
    ws = websocket.WebSocketApp(
        ws_endpoint,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    # Start WebSocket in a separate thread with SSL options
    ssl_options = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False} if ws_url.startswith("wss://") else {}
    ws_thread = threading.Thread(target=lambda: ws.run_forever(sslopt=ssl_options))
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for connection to establish (with timeout)
    if not connection_established.wait(timeout=5):
        print(f"  → WebSocket connection timeout - continuing anyway")
    elif ws_error:
        print(f"  → WebSocket connection failed: {ws_error}")
        try:
            ws.close()
            ws_thread.join(timeout=1)
        except:
            pass
        return False
    
    # 4. Trigger Verification (this should send WebSocket notification)
    try:
        time.sleep(0.5)  # Small delay to ensure proximity is stored
        verify_resp = requests.post(f"{API_URL}/session/verify", json={"token": nonce})
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()
        
        verdict = verify_data["verdict"]
        print(f"Verification Verdict: {verdict}")
        
        # Wait for WebSocket message (with timeout)
        if ws_message_received.wait(timeout=5):
            if ws_message_data and ws_message_data.get("type") == "verification_success":
                result = ws_message_data.get("result", {})
                if result.get("verdict") == verdict:
                    print("✅ WebSocket notification received correctly")
                    print(f"  → Notification verdict: {result.get('verdict')}")
                    print(f"  → Notification URL: {result.get('checked_url', 'N/A')}")
                    # Close WebSocket and wait for thread to finish
                    try:
                        ws.close()
                        ws_thread.join(timeout=2)
                    except:
                        pass
                    return True
                else:
                    print(f"❌ WebSocket notification verdict mismatch: {result.get('verdict')} vs {verdict}")
                    try:
                        ws.close()
                        ws_thread.join(timeout=2)
                    except:
                        pass
                    return False
            else:
                print(f"❌ Unexpected WebSocket message type: {ws_message_data}")
                try:
                    ws.close()
                    ws_thread.join(timeout=2)
                except:
                    pass
                return False
        else:
            print("❌ WebSocket notification NOT received (timeout)")
            try:
                ws.close()
                ws_thread.join(timeout=2)
            except:
                pass
            return False
            
    except Exception as e:
        print(f"Failed to verify: {e}")
        try:
            ws.close()
            ws_thread.join(timeout=2)
        except:
            pass
        return False

def test_websocket_no_notification_on_failure(url):
    """
    Test that WebSocket notification is NOT sent when verification fails.
    """
    print(f"--- Testing WebSocket: {url} (No Notification on Failure) ---")
    
    # Convert API_URL to WebSocket URL
    ws_url = API_URL.replace("https://", "wss://").replace("http://", "ws://")
    
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
        return False
    
    # 2. Trigger Verification WITHOUT proximity confirmation (should fail)
    try:
        time.sleep(0.5)
        verify_resp = requests.post(f"{API_URL}/session/verify", json={"token": nonce})
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()
        
        verdict = verify_data["verdict"]
        print(f"Verification Verdict: {verdict}")
        
        # 3. Connect WebSocket AFTER verification (to check if notification was sent)
        # Note: In real scenario, WebSocket would be connected before verification
        # but for this test we check if notification was queued/sent
        ws_message_received = threading.Event()
        ws_message_data = None
        ws_error = None
        connection_established = threading.Event()
        ws = None
        ws_thread = None
        
        def on_message(ws, message):
            nonlocal ws_message_data
            try:
                ws_message_data = json.loads(message)
                print(f"  → WebSocket message received: {ws_message_data.get('type', 'unknown')}")
                ws_message_received.set()
            except Exception as e:
                print(f"  → Error parsing WebSocket message: {e}")
        
        def on_error(ws, error):
            nonlocal ws_error
            ws_error = error
            print(f"  → WebSocket error: {error}")
            connection_established.set()
        
        def on_open(ws):
            print(f"  → WebSocket connected")
            connection_established.set()
        
        ws_endpoint = f"{ws_url}/ws/verification/{nonce}"
        print(f"Connecting to WebSocket: {ws_endpoint}")
        ws = websocket.WebSocketApp(
            ws_endpoint,
            on_message=on_message,
            on_error=on_error,
            on_open=on_open
        )
        
        ssl_options = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False} if ws_url.startswith("wss://") else {}
        ws_thread = threading.Thread(target=lambda: ws.run_forever(sslopt=ssl_options))
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for connection and then check for messages
        if connection_established.wait(timeout=5):
            time.sleep(1)  # Give a moment for any queued messages
        
        # Clean up WebSocket
        try:
            ws.close()
            ws_thread.join(timeout=2)
        except:
            pass
        
        if ws_message_received.is_set():
            print("❌ WebSocket notification received when it shouldn't have been")
            print(f"  → Message: {ws_message_data}")
            return False
        else:
            print("✅ No WebSocket notification (as expected for failed verification)")
            return True
            
    except Exception as e:
        print(f"Failed to verify: {e}")
        if ws:
            try:
                ws.close()
                if ws_thread:
                    ws_thread.join(timeout=2)
            except:
                pass
        return False

def test_websocket_no_proximity_no_notification(url):
    """
    Test that WebSocket notification is NOT sent when proximity is not confirmed.
    """
    print(f"--- Testing WebSocket: {url} (No Proximity = No Notification) ---")
    
    # Convert API_URL to WebSocket URL
    ws_url = API_URL.replace("https://", "wss://").replace("http://", "ws://")
    
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
        return False
    
    # 2. Send BLE Proximity as NOT CONFIRMED (supported but not found) - FIRST
    try:
        proximity_payload = {
            "ble_uuid": "test-uuid-" + nonce[:8],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "found": False,
            "supported": True  # BLE supported but phone not found
        }
        prox_resp = requests.post(
            f"{API_URL}/session/proximity/{nonce}",
            json=proximity_payload
        )
        prox_resp.raise_for_status()
        print(f"  → BLE proximity NOT confirmed (phone not found)")
    except Exception as e:
        print(f"  → Failed to send proximity: {e}")
        return False
    
    # 3. NOW connect WebSocket (right after proximity rejection)
    ws_message_received = threading.Event()
    ws_message_data = None
    ws_error = None
    connection_established = threading.Event()
    ws = None
    ws_thread = None
    
    def on_message(ws, message):
        nonlocal ws_message_data
        try:
            ws_message_data = json.loads(message)
            print(f"  → WebSocket message received: {ws_message_data.get('type', 'unknown')}")
            ws_message_received.set()
        except Exception as e:
            print(f"  → Error parsing WebSocket message: {e}")
    
    def on_error(ws, error):
        nonlocal ws_error
        ws_error = error
        print(f"  → WebSocket error: {error}")
        connection_established.set()
    
    def on_open(ws):
        print(f"  → WebSocket connected")
        connection_established.set()
    
    ws_endpoint = f"{ws_url}/ws/verification/{nonce}"
    print(f"Connecting to WebSocket: {ws_endpoint}")
    ws = websocket.WebSocketApp(
        ws_endpoint,
        on_message=on_message,
        on_error=on_error,
        on_open=on_open
    )
    
    ssl_options = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False} if ws_url.startswith("wss://") else {}
    ws_thread = threading.Thread(target=lambda: ws.run_forever(sslopt=ssl_options))
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for connection
    if not connection_established.wait(timeout=5):
        print(f"  → WebSocket connection timeout")
    
    # 4. Trigger Verification (should fail due to proximity not confirmed)
    try:
        time.sleep(0.5)
        verify_resp = requests.post(f"{API_URL}/session/verify", json={"token": nonce})
        verify_resp.raise_for_status()
        verify_data = verify_resp.json()
        
        verdict = verify_data["verdict"]
        print(f"Verification Verdict: {verdict}")
        
        # Wait a bit to see if WebSocket message arrives (should NOT)
        time.sleep(2)
        
        # Clean up WebSocket
        try:
            ws.close()
            ws_thread.join(timeout=2)
        except:
            pass
        
        if ws_message_received.is_set():
            print("❌ WebSocket notification received when it shouldn't have been")
            print(f"  → Message: {ws_message_data}")
            return False
        else:
            print("✅ No WebSocket notification (as expected - proximity not confirmed)")
            return True
            
    except Exception as e:
        print(f"Failed to verify: {e}")
        if ws:
            try:
                ws.close()
                if ws_thread:
                    ws_thread.join(timeout=2)
            except:
                pass
        return False

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
    
    print("\n=== WEBSOCKET NOTIFICATION TESTS ===")
    test_websocket_verification_success("https://gov.pl")
    test_websocket_no_notification_on_failure("https://evil.com/login")
    test_websocket_no_proximity_no_notification("https://gov.pl")
    
    print("\n=== ALL TESTS COMPLETE ===")

if __name__ == "__main__":
    main()
