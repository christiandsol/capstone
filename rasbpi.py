import json
import asyncio
import time
import websockets
from websockets.typing import Data
import sys
import os
import aiohttp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'berryIMU'))
from gesturetwo import BerryIMUInterface, GestureRecognizer

# SERVER_IP = "mafiacapstone.duckdns.org"
SERVER_IP = "127.0.0.1"
GAME_SERVER_PORT = 5050
WEB_SERVER_PORT = 3001
HTTP_PROTO = "http"

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

async def async_input(prompt: str) -> str:
    """Non-blocking input() that keeps the event loop alive for ping/pong."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

async def handle_debug_vote(ws, name):
    print("\n[Pi] Ready to record vote. Go ahead and vote for a player")
    vote = await async_input("[Pi] Enter a player number (1-8): ")

    if not vote.strip().isnumeric():
        print("[Pi] Vote not numeric, try again")
        return False

    print(f"[Pi] Sending vote for player {vote}...")
    await send_signal_to_server(ws, "target", vote, name)
    return True

def record_gesture_blocking(imu, duration_s: float = 1.0, sample_rate_hz: float = 50.0):
    """Record gesture samples synchronously (run via executor to avoid blocking event loop)."""
    samples = []
    dt = 1.0 / sample_rate_hz
    num_samples = int(duration_s * sample_rate_hz)

    for _ in range(num_samples):
        sample = imu.read_sample()
        samples.append(sample)
        time.sleep(dt)  # fine here since this whole function runs in a thread executor

    return samples

async def notify_web_server_disconnect(name: str):
    web_url = f"{HTTP_PROTO}://{SERVER_IP}:{WEB_SERVER_PORT}"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{web_url}/disconnect-player",
                json={"name": name}
            )
        print(f"[DEBUG] Notified web server to disconnect {name}")
    except Exception as e:
        print(f"[DEBUG] Failed to notify web server: {e}")


async def handle_vote(ws, imu, recognizer, name):
    """
    Handles voting using gesture recognition.
    Flow: Press Enter to start -> Record gesture -> Confirm result
    """
    loop = asyncio.get_event_loop()

    while True:
        print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-8)...")
        await async_input("[Pi] Press Enter to start recording: ")

        print("[Pi] Recording gesture... move the BerryIMU now.")
        # Run blocking IMU recording in executor so pings can still be handled
        samples = await loop.run_in_executor(None, record_gesture_blocking, imu, 1.0, 50.0)

        print("[Pi] Recording complete, recognizing...")
        digit = recognizer.classify(samples)

        if digit is None:
            print("[Pi] Could not recognize gesture. Try again with a clearer movement.")
            continue

        if digit not in range(1, 9):
            print(f"[Pi] Recognized digit {digit}, but only 1-8 are valid. Ignoring.")
            continue

        print(f"[Pi] Recognized gesture as digit {digit} (vote for player {digit})")
        confirm = await async_input(f"[Pi] Confirm vote for player {digit}? (y/n): ")

        if confirm.strip().lower() != "y":
            print("[Pi] Vote cancelled. Recording new gesture...")
            continue

        print(f"[Pi] Sending vote for player {digit}...")
        await send_signal_to_server(ws, "target", str(digit), name)
        return True

async def rpi_helper(ws, name, imu, recognizer):
    global cmd

    try:
        async for message in ws:
            msg = parse_json(message)
            if not msg:
                continue
            print(f"[DEBUG]: {msg}")
            action = msg.get("action")

            if action == "denyJoin":
                pi_reason = msg.get("target")
                print(f"[DEBUG]: Unable to join: {pi_reason}")
                return

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
                success = False
                while not success:
                    if cmd == 'y':
                        vote_task = asyncio.ensure_future(handle_vote(ws, imu, recognizer, name))
                    else:
                        vote_task = asyncio.ensure_future(handle_debug_vote(ws, name))

                    # Race: either the vote completes, or we get a new message from server
                    recv_task = asyncio.ensure_future(ws.recv())
                    done, pending = await asyncio.wait(
                        [vote_task, recv_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Cancel whichever didn't finish
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass

                    if recv_task in done:
                        # Got a server message while voting — handle it
                        try:
                            incoming = parse_json(recv_task.result())
                            if incoming and incoming.get("action") == "disconnect":
                                print("[DEBUG] Disconnecting mid-vote...")
                                return
                            # Any other message just falls through, loop retries
                        except Exception:
                            return

                    if vote_task in done:
                        try:
                            success = vote_task.result()
                        except Exception:
                            success = False

                    if not success:
                        print("[Pi] Vote failed, waiting for next server message...")
                continue

    except websockets.exceptions.ConnectionClosedError:
        print("[DEBUG] Connection closed unexpectedly")
    except Exception as e:
        print(f"[ERROR] Handler error for {name}: {e}")
        import traceback
        traceback.print_exc()


async def rpi_handler(name):
    # uri = f"wss://{SERVER_IP}/ws"
    uri = f"ws://{SERVER_IP}:{GAME_SERVER_PORT}"

    print(f"[DEBUG] Connecting to {uri}")

    try:
        async with websockets.connect(
            uri,
            open_timeout=10,
            close_timeout=10,
            ping_interval=None  # disabled to match server, prevents idle timeout
        ) as ws:
            print('[DEBUG] Connected to server')
            setup_msg = {
                "action": "setup",
                "name": name,
                "target": "rpi"
            }
            await ws.send(json.dumps(setup_msg))
            print(f"[DEBUG] Sent setup message with name: {name}")
            print(f"[DEBUG] Now waiting for message from server to request an action...")

            imu = BerryIMUInterface(debug=False)
            recognizer = GestureRecognizer()
            await rpi_helper(ws, name, imu, recognizer)
    except KeyboardInterrupt:
        print("[DEBUG] Ctrl+C detected, disconnecting cleanly...")
    finally:
        await notify_web_server_disconnect(name)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("[HELP] Script is ran as: `python rasbpi.py <player_name> [OPTIONAL]: -n`")
        print("\t[HELP] -n specifies you aren't using your raspberry pi gesture recognition")
        exit()
    player_name = sys.argv[1]
    if len(sys.argv) > 2:
        global cmd
        if sys.argv[2] == '-n':
            print(f"[DEBUG] Continuing without raspberry pi IMU")
            cmd = 'n'
        else:
            print(f"[DEBUG] Unknown arguments, continuing using raspberry pi IMU")
            cmd = 'y'
    else:
        print(f"[DEBUG] Continuing with raspberry pi IMU")

    print(f"[DEBUG] Starting with player name: {player_name}")
    asyncio.run(rpi_handler(player_name))
