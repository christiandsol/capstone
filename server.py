import util
import sys
import select
import socket
import json
import threading

PORT = 5050
MAX_PLAYERS = 10
player_counter = 0
player_counter_lock = threading.Lock()
clients = {}  # Maps connection to player_id
clients_lock = threading.Lock()
active_threads = []

def handle_client(conn, addr):
    """
    Handle individual client connection.
    This function runs in a separate thread for each client.
    It handles both setup (player ID assignment) and ongoing signals.
    """
    global player_counter
    
    print(f"\n[New Connection] {addr} connected")
    
    player_id = None
    
    try:
        while True:
            # Receive data from client
            conn.settimeout(1.0)  # 1 second timeout
            try:
                data = util.receive_json(conn)
                
                if not data:
                    continue
                
                action = data.get("action", "Unknown")
                
                # Check if this is a setup signal
                if action == "setup":
                    # Check if we've reached max players
                    with player_counter_lock:
                        if player_counter >= MAX_PLAYERS:
                            print(f"[Rejected] {addr} - Maximum players ({MAX_PLAYERS}) reached")
                            error_response = {
                                "error": "Maximum players reached",
                                "max_players": MAX_PLAYERS
                            }
                            error_json = json.dumps(error_response)
                            conn.sendall(error_json.encode("utf-8"))
                            break
                        
                        # Assign player ID
                        player_counter += 1
                        player_id = player_counter
                    
                    # Store client mapping
                    with clients_lock:
                        clients[conn] = player_id
                    
                    print(f"[Setup] Assigned Player ID {player_id} to {addr}")
                    
                    # Send player ID back to client
                    response = {
                        "player_id": player_id
                    }
                    response_json = json.dumps(response)
                    conn.sendall(response_json.encode("utf-8"))
                    
                else:
                    # Regular signal - log it (head position changes, votes, etc.)
                    player = data.get("player", "Unknown")
                    target = data.get("target", "None")
                    print(f"[Signal] Player: {player} | Action: {action} | Target: {target}")
                    
            except socket.timeout:
                # No data available, continue loop
                continue
            except Exception as e:
                if "Connection reset" in str(e) or "Bad file descriptor" in str(e):
                    break
                else:
                    print(f"[Error] Client {addr}: {e}")
                    break
                    
    except Exception as e:
        print(f"[Error] Handling client {addr}: {e}")
    finally:
        # Cleanup when client disconnects
        with clients_lock:
            if conn in clients:
                removed_id = clients[conn]
                del clients[conn]
                print(f"[Disconnected] Player {removed_id} ({addr}) disconnected")
        try:
            conn.close()
        except:
            pass


def accept_connections(server):
    """
    Accept new client connections in a loop.
    This runs in its own thread so the main thread can listen for 'q' to quit.
    """
    print("Waiting for clients to connect...")
    while True:
        try:
            server.settimeout(1.0)
            conn, addr = server.accept()
            
            # Check if we've reached max players before creating thread
            with player_counter_lock:
                if player_counter >= MAX_PLAYERS:
                    print(f"[Rejected] {addr} - Maximum players ({MAX_PLAYERS}) already connected")
                    try:
                        error_response = {
                            "error": "Maximum players reached",
                            "max_players": MAX_PLAYERS
                        }
                        error_json = json.dumps(error_response)
                        conn.sendall(error_json.encode("utf-8"))
                        conn.close()
                    except:
                        pass
                    continue
            
            # Start a new thread to handle this client
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()
            active_threads.append(client_thread)
            
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[Error] Accepting connection: {e}")
            break


def main():
    print("Starting server...")
    
    # Create server socket
    HOST = "0.0.0.0"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(MAX_PLAYERS)
    
    print(f"Server listening on port {PORT}")
    print(f"Maximum players: {MAX_PLAYERS}")
    print("\nServer running. Press 'q' and Enter to quit...")
    print("=" * 50)
    print("Waiting for clients...\n")
    
    # Start thread to accept connections
    accept_thread = threading.Thread(target=accept_connections, args=(server,))
    accept_thread.daemon = True
    accept_thread.start()
    
    try:
        while True:
            # Check if user pressed 'q' (non-blocking)
            if sys.platform == 'win32':
                # Windows
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8').lower()
                    if key == 'q':
                        print("\n" + "=" * 50)
                        print("Quit signal received. Shutting down...")
                        break
            else:
                # Unix-like systems (Mac, Linux)
                ready, _, _ = select.select([sys.stdin], [], [], 0.1)
                if ready:
                    key = sys.stdin.readline().strip().lower()
                    if key == 'q':
                        print("\n" + "=" * 50)
                        print("Quit signal received. Shutting down...")
                        break
                        
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("Server interrupted by Ctrl+C")
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        
        # Close all client connections
        with clients_lock:
            print(f"Disconnecting {len(clients)} active clients...")
            for conn in list(clients.keys()):
                try:
                    conn.close()
                except:
                    pass
        
        # Close server
        try:
            server.close()
        except:
            pass
            
        print("Server shut down successfully")
        print(f"Total players connected during session: {player_counter}")
        print("=" * 50)


if __name__ == "__main__":
    main()
