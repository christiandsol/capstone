import socket
import json
import time

# Raspberry Pi settings
LAPTOP_IP = "172.20.10.3"  # IP of the laptop acting as temporary server
LAPTOP_PORT = 5051         # Port laptop uses to assign player ID

SERVER_IP = "172.20.10.3"   # Main server IP
SERVER_PORT = 5050         # Main server port

# Global variable for player ID
player_id = None
role = None


def receive_player_id_from_laptop():
    """Connect to the laptop (acting as server) to receive assigned player ID"""
    global player_id, role

    while True:
        print("HERE")
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
        except Exception as e:
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
    sock = connect()

    # Step 2: Send initial handshake
    send_signal_to_server(sock, "setup", "raspberry_pi")

    try:
        while True:  # persistent loop to continuously ask for votes/actions
            action = input("Enter action (vote/targeted) or 'q' to quit: ")
            if action.lower() == "q":
                print("[Pi] Quitting...")
                break

            target = None
            if action.lower() in ["vote", "targeted"]:
                try:
                    target = int(input("Enter vote target player ID: "))
                except ValueError:
                    print("[Pi] Invalid input, must be an integer.")
                    continue

            send_signal_to_server(sock, action, target)
            time.sleep(0.1)  # optional, gives a tiny delay between sends

    except KeyboardInterrupt:
        print("\n[Pi] Exiting...")

    finally:
        sock.close()  # only close once at the very end

# def main():
#     # Step 1: Connect to laptop to receive player ID
#     receive_player_id_from_laptop()
#     socket = connect()
#     # send initial handshake signal
#     send_signal_to_server(socket, "setup", "raspberry_pi")
#
#     try:
#         action = input("Enter action (vote/targeted) or 'q' to quit: ")
#
#         target = None
#         if action.lower() == "vote" or action.lower() == "targeted":
#             target = int(input("Enter vote target player ID: "))
#
#         send_signal_to_server(socket, action, target)
#
#     except KeyboardInterrupt:
#         print("\n[Pi] Exiting...")
#         socket.close()


if __name__ == "__main__":
    main()
