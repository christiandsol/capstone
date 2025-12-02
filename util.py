import socket
import json
from typing import Optional
from typing import Dict
from typing import Union


# Number to body attribute mappings
NOSE = 1
CHIN = 152
FOREHEAD = 10


## ip address
# RECEIVER_IP = "192.168.1.108"   # <-- put receiver's IP address here
# PORT = 5050                   # must match the receiver's port

def client_connect(RECEIVER_IP, PORT):
    """
    @param RECEIVER_IP: ip address of the server/receiver
    @param PORT: port you are socketing with (default to 5050)

    If you are the client, this connects you to the server
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(10)
    client.connect((RECEIVER_IP, PORT))
    return client

def server_connect(PORT):
    """
    @param PORT: port to listen to (default 5050)

    Returns: (conn, server)
    conn: actual connection socket for receiving data
    server: listening socket that listens for data, must close to end
    """
    HOST = "0.0.0.0"
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)

    print(f"Listening for a connection on port {PORT}...")

    conn, addr = server.accept()
    print(f"Connected by {addr}")
    return (conn, server)

def receive_json(conn: socket.socket) -> Dict[str, Union[str, int]]:
    """
    @param conn: connection socket that connected with client
    Receives data from the socket and converts it to a Python dictionary.
    """
    data_bytes = conn.recv(4096)
    data_str = data_bytes.decode("utf-8")
    try:
        message = json.loads(data_str)
    except json.JSONDecodeError:
        # print("Error decoding JSON")
        return {}
    return message


def send_json(client: socket.socket ,player_id: int, action: str, target: Optional[str]):
    """
    @param player_id: number that identifies the player
    @param action: action taken ("vote", "kill", "heal", "headUp", "headDown")

    Sends over to server JSON with the data
    """
    data = {
        "player": player_id,
        "action": action,
        "target": target
    }
    json_message = json.dumps(data)
    client.sendall(json_message.encode("utf-8"))

############### DEBUGGING ##############
def print_dic(dic: Dict[str, Union[str, int]]):
    """
    @param dic: dictionary you want to print

    Function: prints the dictionary in a readable format
    """
    if not dic:
        print("Dictionary is empty.")
        return

    print("Dictionary contents:")
    for key, value in dic.items():
        print(f"  {key}: {value}")

#################### CLOSING CONNECTIONS #############################
def client_close(client: socket.socket):
    """
    closes connection on client side
    """
    client.close()
def server_close(server: socket.socket):
    """
    closes connection on server side
    """
    server.close()
def conn_close(conn: socket.socket):
    """
    closes connection
    """
    conn.close()

