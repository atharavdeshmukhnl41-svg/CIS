import requests

try:
    response = requests.get('http://127.0.0.1:9000/vms', timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
