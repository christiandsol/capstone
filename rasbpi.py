import socket
import json
import time

# Raspberry Pi settings
LAPTOP_IP = "172.16.7.4"  # IP of the laptop acting as temporary server
LAPTOP_PORT = 5051         # Port laptop uses to assign player ID

SERVER_IP = "172.16.7.4"   # Main server IP
SERVER_PORT = 5050         # Main server port

# Global variable for player ID
player_id = None
role = None


def receive_player_id_from_laptop():
    """Connect to the laptop (acting as server) to receive assigned player ID"""
    global player_id, role

    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((LAPTOP_IP, LAPTOP_PORT))
            print("[Pi] Connected to laptop, waiting for player ID...")

            data = s.recv(1024)
            if data:
                msg = json.loads(data.decode())
                player_id = msg.get("player_id")
                role = msg.get("role")
                print("[Pi] Assigned player ID: {}".format(player_id))
                print("[Pi] Assigned role: {}".format(role))
            s.close()
            break
        except ConnectionRefusedError:
            print("[Pi] Laptop not ready yet, retrying in 1s...")
            time.sleep(1)


def connect():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_IP, SERVER_PORT))
        return sock

def send_signal_to_server(socket, action, target=None):
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

    try:
        socket.sendall(json.dumps(msg).encode('utf-8'))
        print("[Pi] Sent signal to server: {}".format(msg))
    except Exception as e:
        print("[Pi] Failed to send signal to server:", e)


def main():
    # Step 1: Connect to laptop to receive player ID
    receive_player_id_from_laptop()
    socket = connect()
    # send initial handshake signal
    send_signal_to_server(socket, "setup", "raspberry_pi")

    try:
        action = input("Enter action (vote/targeted) or 'q' to quit: ")

        target = None
        if action.lower() == "vote" or action.lower() == "targeted":
            target = int(input("Enter vote target player ID: "))

        send_signal_to_server(socket, action, target)

    except KeyboardInterrupt:
        print("\n[Pi] Exiting...")
        socket.close()


if __name__ == "__main__":
    main()
