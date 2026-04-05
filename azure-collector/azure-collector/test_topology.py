#!/usr/bin/env python3
"""
Test the topology endpoint
"""

import requests

try:
    response = requests.get("http://localhost:9000/topology")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")