import requests
import json

try:
    res = requests.post("http://localhost:8000/login", json={"email": "arjun@mehtagarments.com", "password": "demo123"})
    print(json.dumps(res.json(), indent=2))
except Exception as e:
    print(f"Failed: {e}")
