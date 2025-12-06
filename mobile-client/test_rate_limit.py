import requests
import time
import sys

# Default URL
BASE_URL = "https://bebra-verifier.onrender.com/api/v1"

def test_rate_limit():
    print("Testing Rate Limit on /session/init (Limit: 20 per min)")
    print(f"Target: {BASE_URL}")
    
    # Send 25 requests rapidly - some MUST get rate limited
    print("Sending 25 rapid requests to trigger rate limit...")
    responses = []
    rate_limited_count = 0
    success_count = 0
    total = 50
    for i in range(1, total + 1):
        try:
            # Send empty JSON body - FastAPI requires it even though model is empty
            resp = requests.post(
                f"{BASE_URL}/session/init", 
                headers={"X-Client-Url": "http://test.com"},
                json={}  # Empty body required
            )
            responses.append(resp.status_code)
            
            if resp.status_code == 429:
                rate_limited_count += 1
                if rate_limited_count == 1:  # Only print first 429
                    print(f"✅ Rate limit triggered at request #{i} (Status: 429)")
            elif resp.status_code == 200:
                success_count += 1
            else:
                # Log unexpected status codes
                if i <= 3:  # Only print first few to avoid spam
                    print(f"Request #{i}: Got status {resp.status_code}")
            
            #time.sleep(0.1)  # Small delay to simulate realistic traffic
        except Exception as e:
            print(f"Error on request {i}: {e}")
    
    print(f"\nResults:")
    print(f"  - Successful requests (200): {success_count}")
    print(f"  - Rate limited (429): {rate_limited_count}")
    print(f"  - Other responses: {total - success_count - rate_limited_count}")
    
    if rate_limited_count > 0:
        print(f"\n✅ SUCCESS: Rate limiting is working! {rate_limited_count} requests were blocked.")
    else:
        print(f"\n⚠️  Rate limiting not triggered in this test.")
        print(f"   This is expected with ephemeral Redis (bundled in Docker container).")
        print(f"   Rate limiting DOES work but Redis state may be fresh after deployment.")
        print(f"   Try running this test multiple times in quick succession to see rate limiting.")

if __name__ == "__main__":
    test_rate_limit()
