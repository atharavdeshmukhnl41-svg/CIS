import requests
 
def check_http(ip, port):
    try:
        res = requests.get(f"http://{ip}:{port}", timeout=2)
        return True
    except:
        return False