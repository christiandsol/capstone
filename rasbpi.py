import socket
import json
import time

# Raspberry Pi settings
LAPTOP_IP = "172.16.7.4"  # Replace with the laptop IP
LAPTOP_PORT = 5051             # Port laptop uses to assign player ID

SERVER_IP = "172.16.7.4"   # Main server IP
SERVER_PORT = 5050             # Main server port

# Global variable for player ID
player_id = None

def receive_player_id():
    """Connect to laptop to receive assigned player ID"""
    global player_id

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((LAPTOP_IP, LAPTOP_PORT))
    print("[Pi] Connected to laptop, waiting for player ID...")

    data = s.recv(1024)
    if data:
        msg = json.loads(data.decode())
        player_id = msg.get("player_id")
        print(f"[Pi] Assigned player ID: {player_id}")

    s.close()

def send_signal_to_server(action, target=None):
    """Send a signal to the main server using the global player_id"""
    global player_id
    if player_id is None:
        print("[Pi] ERROR: Player ID not assigned yet")
        return

    msg = {
        "player": player_id,
        "action": action,
        "target": target
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_IP, SERVER_PORT))
    sock.sendall(json.dumps(msg).encode())
    sock.close()
    print(f"[Pi] Sent signal to server: {msg}")

def main():
    # Step 1: Receive assigned player ID from laptop
    receive_player_id()

    # Step 2: Use player ID to send signals (replace with your own logic)
    try:
        while True:
            action = input("Enter action (headUp/headDown/vote) or 'q' to quit: ")
            if action.lower() == "q":
                break

            target = None
            if action == "vote":
                target = int(input("Enter vote target player ID: "))

            send_signal_to_server(action, target)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[Pi] Exiting...")

if __name__ == "__main__":
    main()

