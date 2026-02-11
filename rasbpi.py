import json
import asyncio
import time
import websockets
from websockets.typing import Data
import sys
import os
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesturetwo import BerryIMUInterface, GestureRecognizer

SERVER_IP = "mafiacapstone.duckdns.org"
# SERVER_IP = "127.0.0.1"

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

# Use a queue to communicate between input thread and async code
input_queue = asyncio.Queue()

def input_thread_worker(prompt: str):
    """Run in a separate thread to get input without blocking the event loop"""
    result = input(prompt)
    asyncio.run_coroutine_threadsafe(input_queue.put(result), loop)

async def async_input(prompt: str = ""):
    """Non-blocking input using a separate thread"""
    # Start input in background thread
    thread = threading.Thread(target=input_thread_worker, args=(prompt,), daemon=True)
    thread.start()
    # Wait for the result
    return await input_queue.get()

async def handle_debug_vote(ws, name):
    print("\n[Pi] Ready to record vote. Go ahead and vote for a player")
    vote = await async_input("[Pi] Enter a player number (1-8): ")
    
    if not vote.strip().isnumeric():
        print("[Pi] Vote not numeric, try again")
        return False
    
    action = "target"
    print(f"[Pi] Sending vote for player {vote}...")
    await send_signal_to_server(ws, action, vote, name)
    return True

async def handle_vote(ws, imu, recognizer, name):
    """
    Handles the voting using gesture recognition
    """
    print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-8)...")
    
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
        return False
    
    if digit not in range(1, 9):
        print(f"[Pi] Recognized digit {digit}, but only 1-8 are valid. Ignoring.")
        return False
    
    # Ask for confirmation before sending vote
    print(f"[Pi] Recognized gesture as digit {digit} (vote for player {digit})")
    confirm = await async_input(f"[Pi] Confirm vote for player {digit}? (y/n): ")
    
    if confirm.strip().lower() != "y":
        print("[Pi] Vote cancelled.")
        return False
    
    # Set action and target based on gesture recognition
    action = "target"
    target = digit
    
    print(f"[Pi] Sending vote for player {digit}...")
    await send_signal_to_server(ws, action, target, name)
    return True

async def rpi_helper(ws, name, imu, recognizer):
    print("[Pi] Are you running on your raspberry pi? (y for raspberry pi, n for local debugging): ", end='')
    cmd = await async_input()
    cmd = cmd.strip().lower()
    
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
            
            # Only handle voting when the server asks us to (vote, kill, save)
            if action in ["vote", "kill", "save"]:
                if cmd == 'y':
                    success = await handle_vote(ws, imu, recognizer, name)
                    if not success:
                        print("[Pi] Vote failed, waiting for next server message...")
                else:
                    success = await handle_debug_vote(ws, name)
                    if not success:
                        print("[Pi] Vote failed, waiting for next server message...")
                # Continue to next message without breaking
                continue
                
    except websockets.exceptions.ConnectionClosedError:
        print(f"[DEBUG] Connection closed unexpectedly")
    except Exception as e:
        print(f"[ERROR] Handler error for {name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[DEBUG] Player leaving...")

async def rpi_handler(name):
    global loop
    loop = asyncio.get_event_loop()
    
    # uri = f"ws://{SERVER_IP}:{SERVER_PORT}"
    uri = f"wss://{SERVER_IP}/ws"

    print(f"[DEBUG] Connecting to {uri}")

    async with websockets.connect(uri, open_timeout=None, close_timeout=None, ping_interval=None, ping_timeout=None) as ws:
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
