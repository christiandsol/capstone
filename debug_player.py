import asyncio
import json
import websockets

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5050

async def debug_player(player_name):
    uri = f"ws://{SERVER_IP}:{SERVER_PORT}"
    
    async with websockets.connect(uri, ping_interval = 30, ping_timeout = 30) as ws:
        # Send setup
        await ws.send(json.dumps({
            "action": "setup",
            "name": player_name,
            "target": "rpi"
        }))
        print(f"[{player_name}] Connected and sent setup")
        
        async for message in ws:
            msg = json.loads(message)
            print(f"[{player_name}] Received: {msg}")
            
            action = msg.get("action")
            if action in ["civilian", "mafia", "doctor"]:
                print(f"[{player_name}] Role: {action}")
                continue
            
            # When it's voting time
            vote = input(f"[{player_name}] Enter vote (1-4): ").strip()
            print(f'[DEBUG] Registered vote: {vote}')
            await ws.send(json.dumps({
                "action": "targeted",
                "name": player_name,
                "target": vote
            }))

if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "DebugPlayer"
    asyncio.run(debug_player(name))
