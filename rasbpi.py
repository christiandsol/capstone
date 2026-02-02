import threading
import json
import asyncio
import time
from flask import Flask
from threading import Event
import websockets
from websockets.typing import Data
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesture import BerryIMUInterface, GestureRecognizer

SERVER_IP = "172.16.12.134"
SERVER_PORT = 5050

def parse_json(message: Data): ## new parse_json
    try:
        parsed = json.loads(message)
        print(parsed)
        return parsed
    except json.JSONDecodeError:
        print("Invalid JSON:", message)
        return None

app = Flask(__name__)
CORS(app)

name = None
name_ready = Event()

@app.route("/api/<incoming_name>", methods=["POST"])
def save_name(incoming_name: str) -> str:
    global name
    name = incoming_name
    name_ready.set()
    print(f"[HTTP SERVER] received name: {incoming_name}")
    return incoming_name


async def send_signal_to_server(ws, action, target):
    global name
    msg = {
        "action": action,
        "name": name,
        "target": target
    }

    await ws.send(json.dumps(msg))



async def handle_vote(ws, imu, recognizer):
    """
    Handles the voting
    """
    global name
    while True:
        print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-4)...")
        print("[Pi] Press Enter to start recording, or 'q' to quit: ", end='')
        cmd = input().strip().lower()
        
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
        await send_signal_to_server(ws, action, target)
        time.sleep(0.1)  # optional, gives a tiny delay between sends


async def rpi_helper(ws,name,imu, recognizer):
    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue
            # server tells us it's our turn to vote
            await handle_vote(ws, imu, recognizer)
    except websockets.exceptions.ConnectionClosedError:
        print(f"[DEBUG] Connection closed unexpectedly")
    except Exception as e:
        print(f"[ERROR] Handler error for {name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[DEBUG] Player leaving...")


async def rpi_handler(name):
    uri = f"ws://{SERVER_IP}:{SERVER_PORT}"
    print(f"[DEBUG] Connecting to {uri}")

    async with websockets.connect(uri) as ws:
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


def main():
    global name
    print("[DEBUG] Waiting for player name")
    name_ready.wait()
    print("[DEBUG] Now connecting to server")
    asyncio.run(rpi_handler(name))

if __name__ == "__main__":
    threading.Thread(target=main, daemon=True).start()
    app.run(port=8000, use_reloader = False)

