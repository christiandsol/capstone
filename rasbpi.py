import socket
import json
import time
import sys
import os

# Add berryIMU directory to path to import gesture recognition
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesture import BerryIMUInterface, GestureRecognizer

# Raspberry Pi settings
LAPTOP_IP = "10.65.171.234"  # IP of the laptop acting as temporary server,  changed this for pose to per user
LAPTOP_PORT = 5051         # Port laptop uses to assign player ID

SERVER_IP = "10.65.171.192"   # Main server IP
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
    print("HERE")
    receive_player_id_from_laptop()
    sock = connect()
    print("HERE 2")

    # Step 2: Send initial handshake
    send_signal_to_server(sock, "setup", "raspberry_pi")

    # Initialize gesture recognition
    imu = BerryIMUInterface(debug=False)
    recognizer = GestureRecognizer()

    try:
        while True:  # persistent loop to continuously ask for votes/actions
            print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-4)...")
            print("[Pi] Press Enter to start recording, or 'q' to quit: ", end='')
            cmd = input().strip().lower()
            
            if cmd == "q":
                print("[Pi] Quitting...")
                break

            # Record gesture sequence (1 second)
            print("[Pi] Recording gesture... move the BerryIMU now.")
            samples = []
            duration_s = 1.0
            sample_rate_hz = 50.0
            dt = 1.0 / sample_rate_hz
            num_samples = int(duration_s * sample_rate_hz)
            
            for i in range(num_samples):
                sample = imu.read_sample()
                samples.append(sample)
                time.sleep(dt)
            
            print("[Pi] Recording complete, recognizing...")
            
            # Classify the gesture
            digit = recognizer.classify(samples)
            
            if digit is None:
                print("[Pi] Could not recognize gesture. Try again with a clearer movement.")
                continue
            
            if digit not in (1, 2, 3, 4):
                print(f"[Pi] Recognized digit {digit}, but only 1-4 are valid. Ignoring.")
                continue
            
            # Ask for confirmation before sending vote
            print(f"[Pi] Recognized gesture as digit {digit} (vote for player {digit})")
            confirm = input(f"[Pi] Confirm vote for player {digit}? (y/n): ").strip().lower()
            
            if confirm != "y":
                print("[Pi] Vote cancelled. Recording new gesture...")
                continue  # Go back to the start of the loop to record again
            
            # Set action and target based on gesture recognition
            action = "targeted"
            target = digit
            
            print(f"[Pi] Sending vote for player {digit}...")
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
