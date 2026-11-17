import requests

try:
    r = requests.get("http://127.0.0.1:5000/")
    print(f"Server alive! Status: {r.status_code}, Length: {len(r.text)}")
except Exception as e:
    print(f"Connection failed: {e}")

