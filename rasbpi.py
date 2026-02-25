import json
import asyncio
import time
import websockets
from websockets.typing import Data
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesturetwo import BerryIMUInterface, GestureRecognizer

# SERVER_IP = "mafiacapstone.duckdns.org"
SERVER_IP = "127.0.0.1"

SERVER_PORT = 5050

def parse_json(message: Data):
    try:
        parsed = json.loads(message)
        print(parsed)
        return parsed
    except json.JSONDecodeError:
        print("Invalid JSON:", message)
        return None

async def send_signal_to_server(ws, action, target, name):
    msg = {
        "action": action,
        "name": name,
        "target": target
    }
    await ws.send(json.dumps(msg))

async def handle_debug_vote(ws, name):
    print("\n[Pi] Ready to record vote. Go ahead and vote for a player")
    vote = input("[Pi] Enter a player number (1-8): ")

    if not vote.strip().isnumeric():
        print("[Pi] Vote not numeric, try again")
        return False

    print(f"[Pi] Sending vote for player {vote}...")
    await send_signal_to_server(ws, "target", vote, name)
    return True

def record_gesture_blocking(imu, duration_s: float = 1.0, sample_rate_hz: float = 50.0):
    """Record gesture samples. Returns the list of samples."""
    samples = []
    dt = 1.0 / sample_rate_hz
    num_samples = int(duration_s * sample_rate_hz)

    for _ in range(num_samples):
        sample = imu.read_sample()
        samples.append(sample)
        time.sleep(dt)

    return samples

async def handle_vote(ws, imu, recognizer, name):
    """
    Handles voting using gesture recognition.
    Flow: Press Enter to start -> Record gesture -> Confirm result
    """
    while True:
        print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-8)...")
        input("[Pi] Press Enter to start recording: ")

        print("[Pi] Recording gesture... move the BerryIMU now.")
        samples = record_gesture_blocking(imu, 1.0, 50.0)

        print("[Pi] Recording complete, recognizing...")
        digit = recognizer.classify(samples)

        if digit is None:
            print("[Pi] Could not recognize gesture. Try again with a clearer movement.")
            continue

        if digit not in range(1, 9):
            print(f"[Pi] Recognized digit {digit}, but only 1-8 are valid. Ignoring.")
            continue

        print(f"[Pi] Recognized gesture as digit {digit} (vote for player {digit})")
        confirm = input(f"[Pi] Confirm vote for player {digit}? (y/n): ")

        if confirm.strip().lower() != "y":
            print("[Pi] Vote cancelled. Recording new gesture...")
            continue

        print(f"[Pi] Sending vote for player {digit}...")
        await send_signal_to_server(ws, "target", str(digit), name)
        return True

async def rpi_helper(ws, name, imu, recognizer):
    cmd = input("[Pi] Are you running on your raspberry pi? (y for raspberry pi, n for local debugging): ")
    cmd = cmd.strip().lower()

    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue
            print(f"[DEBUG]: {msg}")
            action = msg.get("action")

            if action in ["civilian", "mafia", "doctor"]:
                print(f"[DEBUG] received role: {action}")
                continue

            if action == "disconnect":
                print("[DEBUG] Disconnecting...")
                return

            if action == "restart_status":
                print("[DEBUG] Received restart, restarting game, your role may change")
                continue

            if action in ["vote", "kill", "save"]:
                if cmd == 'y':
                    success = await handle_vote(ws, imu, recognizer, name)
                else:
                    success = await handle_debug_vote(ws, name)

                if not success:
                    print("[Pi] Vote failed, waiting for next server message...")
                continue

    except websockets.exceptions.ConnectionClosedError:
        print("[DEBUG] Connection closed unexpectedly")
    except Exception as e:
        print(f"[ERROR] Handler error for {name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[DEBUG] Player leaving...")

async def rpi_handler(name):
    # uri = f"wss://{SERVER_IP}/ws"
    uri = f"ws://{SERVER_IP}:{SERVER_PORT}"
    
    print(f"[DEBUG] Connecting to {uri}")

    async with websockets.connect(uri, open_timeout=10, close_timeout=10, ping_interval=20, ping_timeout=20) as ws:
        print('[DEBUG] Connected to server')
        setup_msg = {
            "action": "setup",
            "name": name,
            "target": "rpi"
        }
        await ws.send(json.dumps(setup_msg))
        print(f"[DEBUG] Sent setup message with name: {name}")

        imu = BerryIMUInterface(debug=False)
        recognizer = GestureRecognizer()
        await rpi_helper(ws, name, imu, recognizer)

if __name__ == "__main__":
    player_name = sys.argv[1] if len(sys.argv) > 1 else "RaspberryPiPlayer"
    print(f"[DEBUG] Starting with player name: {player_name}")
    asyncio.run(rpi_handler(player_name))
