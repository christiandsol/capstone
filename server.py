import asyncio
import random
from typing import Dict, List, Optional
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from util import send_json, parse_json
from MafiaGame import MafiaGame

HOST = "0.0.0.0"
PORT = 5050

# Voice command codes
VOICE_COMMAND_READY_ASSIGN = 2  # "assign players" → mark ready during LOBBY
VOICE_COMMAND_READY_VOTE = 3    # "ready to vote"  → mark ready during READYTOVOTE



# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

lock = asyncio.Lock()
game: MafiaGame = MafiaGame()


# ---------------------------------------------------------------------------
# Per-connection handler
# ---------------------------------------------------------------------------

async def handler(ws: WebSocketServerProtocol):
    player_name: Optional[str] = None

    try:
        async for msg_text in ws:
            msg = parse_json(msg_text)
            if not msg:
                continue

            action = msg.get("action")

            # ----------------------------------------------------------------
            # Voice commands
            # ----------------------------------------------------------------
            if action == "control":
                ctrl_code = msg.get("target")

                if ctrl_code == VOICE_COMMAND_READY_ASSIGN and game.state == "LOBBY":
                    print(f"[VOICE] {player_name} said 'assign players'")
                    if player_name and player_name in game.players:
                        async with lock:
                            game.players[player_name]["ready"] = True
                            await game.broadcast_lobby_status()
                            await game.update()
                    continue

                if ctrl_code == VOICE_COMMAND_READY_VOTE and game.state == "READYTOVOTE":
                    print(f"[VOICE] {player_name} said 'ready to vote'")
                    if player_name and player_name in game.players:
                        async with lock:
                            game.players[player_name]["ready_to_vote"] = True
                            await game.update()
                    continue

                print(f"[VOICE] Unhandled code={ctrl_code} from {player_name}")
                continue

            # ----------------------------------------------------------------
            # Setup: player joining or RPi registering
            # ----------------------------------------------------------------
            if action == "setup":
                incoming_name: Optional[str] = msg.get("target")

                # RPi registration
                if incoming_name == "rpi":
                    rpi_player_name = msg.get("name")
                    print(f"[DEBUG] RPi registered for player: {rpi_player_name}")
                    game.rpis[rpi_player_name] = ws
                    player_name = rpi_player_name
                    continue

                # Web client joining
                player_name = incoming_name
                if player_name in game.players or game.game_started or player_name not in game.rpis:
                    reason = ""
                    if player_name in game.players:
                        reason = f"Name '{player_name}' is already taken"
                    elif game.game_started:
                        reason = "Game has already started — wait for the next game"
                    elif player_name not in game.rpis:
                        reason = f"Raspberry pi with name {player_name} doesn't exist, you must connect with raspberry pi first before here"
                    print(f"[DEBUG] Join denied for '{player_name}': {reason}")
                    await send_json(ws, player_name, "denyJoin", reason)
                    player_name = None
                    await ws.close(1008, "Join denied")
                    continue

                async with lock:
                    if player_name in game.players:
                        await ws.close(1008, "Name already taken")
                        return
                    if len(game.players) >= game.max_players:
                        await ws.close(1008, "Game is full")
                        return

                    player_id = len(game.players) + 1
                    game.player_id_to_name[player_id] = player_name
                    game.name_to_player_id[player_name] = player_id
                    game.clients[ws] = player_name
                    game.players[player_name] = {
                        "ready": False,
                        "ready_to_vote": False,
                        "restart": False,
                        "head": "up",
                        "vote": None,
                        "kill": None,
                        "save": None,
                        "alive": True,
                    }

                await send_json(ws, player_name, "acceptJoin", None)
                await send_json(ws, player_id, "id_registered", None)
                print(f"[DEBUG] {player_name} joined (ID {player_id})")
                await game.broadcast_lobby_status()
                continue

            # ----------------------------------------------------------------
            # Ready signal
            # ----------------------------------------------------------------
            if action == "ready":
                if player_name and player_name in game.players:
                    async with lock:
                        game.players[player_name]["ready"] = True
                        print(f"[DEBUG] {player_name} is ready")
                        await game.broadcast_lobby_status()
                        await game.update()
                continue

            # ----------------------------------------------------------------
            # Restart vote
            # ----------------------------------------------------------------
            if action == "restart":
                if player_name and player_name in game.players and game.state == "GAMEOVER":
                    async with lock:
                        game.players[player_name]["restart"] = True
                        print(f"[DEBUG] {player_name} wants to restart")
                        await game.broadcast_restart_status()
                        await game.update()
                continue

            # ----------------------------------------------------------------
            # In-game signals (head position, kill/save/vote targets)
            # ----------------------------------------------------------------
            if player_name and game.valid_signal(msg):
                async with lock:
                    if player_name not in game.players:
                        print("[DEBUG] Player Name is not registered")
                        continue

                    player_data = game.players[player_name]

                    if action == "headUp":
                        player_data["head"] = "up"

                    elif action == "headDown":
                        player_data["head"] = "down"

                    elif action in ("voiceCommand", "target"):
                        raw_target = msg.get("target")
                        print(f"[DEBUG] Target signal from {player_name}: {raw_target!r}")

                        # RPis send numeric player IDs — resolve to player_name
                        if isinstance(raw_target, str) and raw_target.isnumeric():
                            raw_target = int(raw_target)
                        if isinstance(raw_target, int):
                            resolved = game.id_to_name(raw_target)
                            if resolved is None:
                                print(f"[DEBUG] Unknown player ID: {raw_target}")
                                continue
                            raw_target = resolved

                        target_name: str = raw_target

                        if player_name in game._active_mafia_names() and game.state == "MAFIAVOTE":
                            player_data["kill"] = target_name
                            print(f"[DEBUG] {player_name} (mafia) targets kill: {target_name}")
                        elif player_name in game._active_doctor_names() and game.state == "DOCTORVOTE":
                            player_data["save"] = target_name
                            print(f"[DEBUG] {player_name} (doctor) targets save: {target_name}")
                        elif game.state == "VOTE":
                            player_data["vote"] = target_name
                            print(f"[DEBUG] {player_name} day-votes: {target_name}")

                await game.update()

    except websockets.exceptions.ConnectionClosedError:
        print(f"[DEBUG] Connection closed unexpectedly for: {player_name}")
    except Exception as e:
        print(f"[ERROR] Handler error for {player_name}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if player_name:
            print(f"[DEBUG] Cleaning up {player_name}")
            async with lock:
                await clean_player(player_name, ws)


async def clean_player(player_name: str, ws: WebSocketServerProtocol):
    """Remove a disconnected player and reset the game if one was in progress"""

    # Notify and disconnect the player's RPi if one is registered
    if player_name in game.rpis:
        rpi_ws = game.rpis[player_name]
        await send_json(rpi_ws, player_name, "disconnect", None)
        del game.rpis[player_name]

    # Remove from web-client tracking
    if ws in game.clients:
        del game.clients[ws]

    # Remove from player registry and ID maps
    if player_name in game.players:
        player_id = game.name_to_player_id.get(player_name)
        if player_id is not None:
            del game.player_id_to_name[player_id]
            del game.name_to_player_id[player_name]
        del game.players[player_name]

    print(f"[DEBUG] {player_name} removed")

    if len(game.players) < 3:
        game.game_started = False

    # If no game was in progress, just refresh the lobby for remaining players
    if game.state == "LOBBY":
        await game.broadcast_lobby_status()
        return

    # Mid-game disconnect — reset everything and send everyone back to lobby
    print(f"[DEBUG] {player_name} left mid-game — resetting to lobby")
    game.reset_game_state()
    await game.broadcast("lobby_reset", player_name)
    await game.broadcast_lobby_status()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with websockets.serve(handler, HOST, PORT, ping_interval=20, ping_timeout=20, close_timeout=10):
        print(f"[SERVER] WebSocket server running on port {PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
