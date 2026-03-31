import psutil
import time
import requests
import socket
 
API = "http://192.168.1.1:8000/ingest"
VM_NAME = socket.gethostname()
 
while True:
    try:
        cpu = psutil.cpu_percent(interval=1)
        net = psutil.net_io_counters()
 
        data = {
            "vm": VM_NAME,
            "cpu": cpu,
            "network_in": net.bytes_recv,
            "network_out": net.bytes_sent
        }
 
        requests.post(API, json=data, timeout=2)
 
    except Exception as e:
        print("Agent error:", e)
 
    time.sleep(5)