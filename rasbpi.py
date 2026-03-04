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

# NOTE: production:
SERVER_IP = "mafiacapstone.duckdns.org"
# NOTE: local development:
# SERVER_IP = "127.0.0.1"
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

async def async_input(prompt: str, reader: asyncio.StreamReader) -> str:
    """Truly cancellable stdin read using asyncio streams."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    line = await reader.readline()
    return line.decode().rstrip('\n')

async def handle_debug_vote(ws, name, reader):
    print("\n[Pi] Ready to record vote. Go ahead and vote for a player")
    vote = await async_input("[Pi] Enter a player number (1-8): ", reader)

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
        time.sleep(dt)

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

async def handle_vote(ws, imu, recognizer, name, reader):
    """
    Handles voting using gesture recognition.
    Flow: Press Enter to start -> Record gesture -> Confirm result
    """
    loop = asyncio.get_event_loop()

    while True:
        print("\n[Pi] Ready to record gesture. Move the BerryIMU to vote (1-8)...")
        await async_input("[Pi] Press Enter to start recording: ", reader)

        print("[Pi] Recording gesture... move the BerryIMU now.")
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
        confirm = await async_input(f"[Pi] Confirm vote for player {digit}? (y/n): ", reader)

        if confirm.strip().lower() != "y":
            print("[Pi] Vote cancelled. Recording new gesture...")
            continue

        print(f"[Pi] Sending vote for player {digit}...")
        await send_signal_to_server(ws, "target", str(digit), name)
        return True

async def rpi_helper(ws, name, imu, recognizer, stop_event, reader):
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
                stop_event.set()
                return

            if action in ["civilian", "mafia", "doctor"]:
                print(f"[DEBUG] received role: {action}")
                continue

            if action == "disconnect":
                print("[DEBUG] Disconnecting...")
                stop_event.set()
                return

            if action == "restart_status":
                print("[DEBUG] Received restart, restarting game, your role may change")
                continue

            if action in ["vote", "kill", "save"]:
                success = False
                while not success:
                    if cmd == 'y':
                        vote_task = asyncio.ensure_future(handle_vote(ws, imu, recognizer, name, reader))
                    else:
                        vote_task = asyncio.ensure_future(handle_debug_vote(ws, name, reader))

                    recv_task = asyncio.ensure_future(ws.recv())
                    stop_task = asyncio.ensure_future(stop_event.wait())

                    done, pending = await asyncio.wait(
                        [vote_task, recv_task, stop_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass

                    if stop_task in done or stop_event.is_set():
                        print("[DEBUG] Disconnect received during vote, exiting...")
                        return

                    if recv_task in done:
                        try:
                            incoming = parse_json(recv_task.result())
                            if incoming and incoming.get("action") == "disconnect":
                                print("[DEBUG] Disconnecting mid-vote...")
                                stop_event.set()
                                return
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
    finally:
        stop_event.set()


async def rpi_handler(name):
    # NOTE: production
    uri = f"wss://{SERVER_IP}/ws"
    # NOTE: Local development
    # uri = f"ws://{SERVER_IP}:{GAME_SERVER_PORT}"

    print(f"[DEBUG] Connecting to {uri}")

    stop_event = asyncio.Event()

    # Create stdin reader ONCE, pass it down to avoid thread executor blocking on input()
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    try:
        async with websockets.connect(
            uri,
            open_timeout=10,
            close_timeout=10,
            ping_interval=None
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
            await rpi_helper(ws, name, imu, recognizer, stop_event, reader)

    except KeyboardInterrupt:
        print("[DEBUG] Ctrl+C detected, disconnecting cleanly...")
    finally:
        stop_event.set()
        await notify_web_server_disconnect(name)
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("[HELP] Script is ran as: `python rasbpi.py <player_name> [OPTIONAL]: -n`")
        print("\t[HELP] -n specifies you aren't using your raspberry pi gesture recognition")
        exit()

    player_name = sys.argv[1]

    if len(sys.argv) > 2:
        if sys.argv[2] == '-n':
            print(f"[DEBUG] Continuing without raspberry pi IMU")
            cmd = 'n'
        else:
            print(f"[DEBUG] Unknown arguments, continuing using raspberry pi IMU")
            cmd = 'y'
    else:
        print(f"[DEBUG] Continuing with raspberry pi IMU")
        cmd = 'y'

    print(f"[DEBUG] Starting with player name: {player_name}")
    asyncio.run(rpi_handler(player_name))
