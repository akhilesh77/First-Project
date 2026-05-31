import subprocess
import time
import requests
import json
import sys

def main():
    print("Starting server...")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--app-dir", "src"])
    time.sleep(3) # Wait for server to start
    
    try:
        # Test 1: Locations
        print("\n--- Test 1: Locations ---")
        res = requests.get("http://127.0.0.1:8000/v1/locations")
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            print(f"Count: {len(res.json().get('locations', []))}")
        
        # Test 2: Recommendation (Normal)
        print("\n--- Test 2: Recommendation (Normal) ---")
        req1 = {
            "location": "Bengaluru",
            "budget": "medium",
            "cuisine": "North Indian",
            "min_rating": 4.0,
            "top_k": 5
        }
        res1 = requests.post("http://127.0.0.1:8000/v1/recommendations", json=req1)
        print(f"Status: {res1.status_code}")
        if res1.status_code == 200:
            data = res1.json()
            print(f"Found: {len(data.get('recommendations', []))}")
            for r in data.get('recommendations', []):
                print(f" - {r['name']} ({r['location']}) [{r['cuisine']}]")
        else:
            print(res1.text)
            
    finally:
        print("\nKilling server...")
        server.terminate()
        server.wait()

if __name__ == "__main__":
    main()
