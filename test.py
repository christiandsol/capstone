# test_client.py
import socket

RECEIVER_IP = "172.20.10.11"  # Use actual server IP
PORT = 5050

print(f"Attempting to connect to {RECEIVER_IP}:{PORT}...")

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(10)  # 10 second timeout
    client.connect((RECEIVER_IP, PORT))
    print("✓ CONNECTION SUCCESSFUL!")
    client.send(b"Hello from client")
    client.close()
except socket.timeout:
    print("✗ Connection timed out - server not responding")
except ConnectionRefusedError:
    print("✗ Connection refused - server not listening on this port")
except Exception as e:
    print(f"✗ Error: {e}")