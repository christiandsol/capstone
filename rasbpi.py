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

class AsyncInput:
    """Helper class to handle async input in a thread-safe way"""
    def __init__(self):
        self.loop = None
        self.queue = None
    
    def set_loop(self, loop):
        """Set the event loop after it's created"""
        self.loop = loop
        self.queue = asyncio.Queue(loop=loop)
    
    def input_thread_worker(self, prompt: str):
        """Run in a separate thread to get input without blocking the event loop"""
        result = input(prompt)
        # Schedule the coroutine on the event loop from the thread
        asyncio.run_coroutine_threadsafe(self._put_result(result), self.loop)
    
    async def _put_result(self, result):
        """Put result in queue"""
        await self.queue.put(result)
    
    async def get_input(self, prompt: str = ""):
        """Non-blocking input using a separate thread"""
        if self.loop is None or self.queue is None:
            raise RuntimeError("AsyncInput not initialized with event loop")
        
        # Start input in background thread
        thread = threading.Thread(target=self.input_thread_worker, args=(prompt,), daemon=True)
        thread.start()
        
        # Wait for the result
        return await self.queue.get()

# Global instance
async_input_helper = AsyncInput()

async def handle_debug_vote(ws, name):
    print("\n[Pi] Ready to record vote. Go ahead and vote for a player")
    vote = await async_input_helper.get_input("[Pi] Enter a player number (1-8): ")
    
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
    Flow: Press Enter to start -> Record gesture -> Confirm result
    """
    while True:
        print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-8)...")
        await async_input_helper.get_input("[Pi] Press Enter to start recording: ")
        
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
            await asyncio.sleep(dt)  # Non-blocking sleep that allows event loop to run
        
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
        confirm = await async_input_helper.get_input(f"[Pi] Confirm vote for player {digit}? (y/n): ")
        
        if confirm.strip().lower() != "y":
            print("[Pi] Vote cancelled. Recording new gesture...")
            continue
        
        # Set action and target based on gesture recognition
        action = "target"
        target = digit
        
        print(f"[Pi] Sending vote for player {digit}...")
        await send_signal_to_server(ws, action, target, name)
        return True

async def rpi_helper(ws, name, imu, recognizer):
    print("[Pi] Are you running on your raspberry pi? (y for raspberry pi, n for local debugging): ", end='')
    cmd = await async_input_helper.get_input()
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
    # Set the event loop for async input BEFORE using it
    loop = asyncio.get_event_loop()
    async_input_helper.set_loop(loop)
    
    # uri = f"ws://{SERVER_IP}:{SERVER_PORT}"
    uri = f"wss://{SERVER_IP}/ws"

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
    # Get player name from command line argument
    player_name = sys.argv[1] if len(sys.argv) > 1 else "RaspberryPiPlayer"
    print(f"[DEBUG] Starting with player name: {player_name}")
    asyncio.run(rpi_handler(player_name))
