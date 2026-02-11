import json
import asyncio
import time
import websockets
from websockets.typing import Data
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesturetwo import BerryIMUInterface, GestureRecognizer

SERVER_IP = "mafiacapstone.duckdns.org"
SERVER_PORT = 5050

PING_INTERVAL = 10
PING_TIMEOUT = 5
RECONNECT_DELAY = 5  # seconds


def parse_json(message: Data):
    try:
        parsed = json.loads(message)
        print(parsed)
        return parsed
    except json.JSONDecodeError:
        print("Invalid JSON:", message)
        return None


async def send_signal_to_server(ws, action, target, name):
    msg = {"action": action, "name": name, "target": target}
    try:
        await ws.send(json.dumps(msg))
    except websockets.ConnectionClosed:
        print(f"[WARN] Cannot send to {name}: connection closed")


async def async_input(prompt: str) -> str:
    """Run blocking input() in a separate thread."""
    return await asyncio.to_thread(input, prompt)


async def handle_debug_vote(ws, name):
    while True:
        vote = await async_input("\n[Pi] Ready to vote. Enter player number or 'q' to quit: ")
        vote = vote.strip().lower()
        if vote == "q":
            print("[Pi] Exiting vote.")
            return
        if not vote.isnumeric():
            print("[Pi] Vote not numeric. Try again.")
            continue
        await send_signal_to_server(ws, "target", int(vote), name)
        break


async def handle_vote(ws, imu, recognizer, name):
    while True:
        cmd = await async_input("[Pi] Press Enter to start recording gesture, or 'q' to quit: ")
        if cmd.strip().lower() == "q":
            print("[Pi] Exiting vote.")
            return

        print("[Pi] Recording gesture...")
        samples = []
        duration_s = 1.0
        sample_rate_hz = 50.0
        dt = 1.0 / sample_rate_hz
        for _ in range(int(duration_s * sample_rate_hz)):
            samples.append(imu.read_sample())
            await asyncio.sleep(dt)

        print("[Pi] Recognizing gesture...")
        digit = recognizer.classify(samples)

        if digit not in range(1, 9):
            print(f"[Pi] Recognized {digit}, must be 1-8. Try again.")
            continue

        confirm = await async_input(f"[Pi] Confirm vote for player {digit}? (y/n): ")
        if confirm.strip().lower() != "y":
            print("[Pi] Vote cancelled. Try again.")
            continue

        await send_signal_to_server(ws, "target", digit, name)
        break


async def rpi_helper(ws, name, imu, recognizer):
    cmd = await async_input("[Pi] Running on Pi? (y for Pi, n for local debug): ")
    cmd = cmd.strip().lower()
    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue

            action = msg.get("action")
            if action in ["civilian", "mafia", "doctor"]:
                print(f"[DEBUG] Received role: {action}")
                continue
            elif action == "disconnect":
                print("[DEBUG] Server requested disconnect.")
                return
            elif action == "restart_status":
                print("[DEBUG] Game restarting, role may change.")
                continue

            # Only vote when prompted
            if cmd == 'y':
                await handle_vote(ws, imu, recognizer, name)
            else:
                await handle_debug_vote(ws, name)

    except websockets.ConnectionClosed:
        print(f"[WARN] Connection closed unexpectedly")
    except Exception as e:
        print(f"[ERROR] Handler error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[DEBUG] Player leaving...")


async def rpi_handler(name):
    uri = f"wss://{SERVER_IP}/ws"

    while True:
        try:
            async with websockets.connect(
                uri,
                ping_interval=PING_INTERVAL,
                ping_timeout=PING_TIMEOUT
            ) as ws:
                print(f"[DEBUG] Connected to {uri}")

                setup_msg = {"action": "setup", "name": name, "target": "rpi"}
                await ws.send(json.dumps(setup_msg))
                print(f"[DEBUG] Sent setup message with name: {name}")

                imu = BerryIMUInterface(debug=False)
                recognizer = GestureRecognizer()
                await rpi_helper(ws, name, imu, recognizer)

        except Exception as e:
            print(f"[WARN] Connection failed or lost: {e}")
            print(f"[INFO] Reconnecting in {RECONNECT_DELAY}s...")
            await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    player_name = sys.argv[1] if len(sys.argv) > 1 else "RaspberryPiPlayer"
    print(f"[DEBUG] Starting with player name: {player_name}")
    asyncio.run(rpi_handler(player_name))

