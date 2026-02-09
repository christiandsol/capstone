import json
import asyncio
import time
import websockets
from websockets.typing import Data
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesturetwo import BerryIMUInterface, GestureRecognizer

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
    while True:
        print("\n[Pi] Ready to record vote. Go ahead and vote for a player")
        print("[Pi] Press Enter to start recording, or 'q' to quit: ", end='')
        vote = input().strip().lower()
        if not vote.isnumeric():
            print("[Pi] Vote not numeric, try again", end='')
            continue
        action = "target"

        print(f"[Pi] Sending vote for player {vote}...")
        await send_signal_to_server(ws, action, vote, name)
        break

async def handle_vote(ws, imu, recognizer, name):
    """
    Handles the voting
    """
    while True:
        print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-8)...")
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
        
        if digit not in range(1, 9):
            print(f"[Pi] Recognized digit {digit}, but only 1-8 are valid. Ignoring.")
            continue
        
        # Ask for confirmation before sending vote
        print(f"[Pi] Recognized gesture as digit {digit} (vote for player {digit})")
        confirm = input(f"[Pi] Confirm vote for player {digit}? (y/n): ").strip().lower()
        
        if confirm != "y":
            print("[Pi] Vote cancelled. Recording new gesture...")
            continue
        
        # Set action and target based on gesture recognition
        action = "targeted"
        target = digit
        
        print(f"[Pi] Sending vote for player {digit}...")
        await send_signal_to_server(ws, action, target, name)
        time.sleep(0.1)
        break

async def rpi_helper(ws, name, imu, recognizer):
    print("[Pi] Are you running on your raspberry pi? (y for raspberry pi, n for local debugging): ", end='')
    cmd = input().strip().lower()
    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue
            print(f"[DEBUG]: {msg}")
            action = msg.get("action")
            if action in ["civilian", "mafia", "doctor"]:
                role = action
                print(f"[DEBUG] received role: {action}")
                continue

            if action == "disconnect":
                print("[DEBUG] Disconnecting...")
                return
            if action == "restart_status":
                print("[DEBUG] Received restart, restarting game, your role may change")
                continue
            # Only act when server asks you to
            # if action in ["vote", "kill", "save"]:
            #     if action == "vote":
            #         await handle_vote(ws, imu, recognizer, name)
            #     elif action == "kill" or action == "save":
            #         await handle_vote(ws, imu, recognizer, name)
        
            # server tells us it's our turn to vote
            if cmd == 'y':
                await handle_vote(ws, imu, recognizer, name)
            else:
                await handle_debug_vote(ws, name)
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
    # uri = f"wss://{SERVER_IP}/ws"

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

if __name__ == "__main__":
    # Get player name from command line argument
    player_name = sys.argv[1] if len(sys.argv) > 1 else "RaspberryPiPlayer"
    print(f"[DEBUG] Starting with player name: {player_name}")
    asyncio.run(rpi_handler(player_name))
