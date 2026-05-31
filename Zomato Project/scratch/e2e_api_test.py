import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_locations():
    print("Testing /v1/locations...")
    resp = requests.get(f"{BASE_URL}/v1/locations")
    if resp.status_code != 200:
        print(f"FAILED: Locations endpoint returned {resp.status_code}")
        return False
    data = resp.json()
    if not data.get("locations"):
        print("FAILED: No locations returned")
        return False
    print(f"SUCCESS: Locations fetched ({len(data['locations'])})")
    return True

def test_recommendations():
    print("Testing /v1/recommendations...")
    payload = {
        "location": "Bengaluru",
        "budget": "medium",
        "cuisine": "North Indian",
        "min_rating": 4.0,
        "top_k": 5
    }
    resp = requests.post(f"{BASE_URL}/v1/recommendations", json=payload)
    if resp.status_code != 200:
        print(f"FAILED: Recommendations endpoint returned {resp.status_code} - {resp.text}")
        return False
    data = resp.json()
    recs = data.get("recommendations", [])
    print(f"SUCCESS: Recommendations fetched ({len(recs)})")
    
    # Check for duplicates
    names = [r["name"] for r in recs]
    if len(names) != len(set(names)):
        print(f"FAILED: Duplicate restaurants found! {names}")
        return False
    
    # Check API fields
    for r in recs:
        if "restaurant_id" not in r or "name" not in r:
            print(f"FAILED: Missing fields in recommendation {r}")
            return False
            
    print("SUCCESS: Recommendations format valid and no duplicates found.")
    return True

if __name__ == "__main__":
    loc_ok = test_locations()
    rec_ok = test_recommendations()
    if loc_ok and rec_ok:
        print("All API tests passed.")
        sys.exit(0)
    else:
        print("Some API tests failed.")
        sys.exit(1)
