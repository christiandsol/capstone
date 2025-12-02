import cv2
import time
import mediapipe as mp
import platform
import socket
from typing import Optional
from typing import List
from player import Player
from util import print_dic, send_json, receive_json, client_connect, client_close, NOSE, CHIN, FOREHEAD

mp_face = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils


# DATAFORMAT: 
# {
#     "player": player_id,
#     "action": "vote/kill/heal/headmovement/setup"
#     "target": player_id/null
# }

class Pose:
    def __init__(self, pi_ip: str, pi_port: int):
        self.pi_ip = pi_ip
        self.pi_port = pi_port
        self.numPeople = 1

    def connect_to_pi(self) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[Pi] Connecting to Raspberry Pi at {self.pi_ip}:{self.pi_port}...")
        s.connect((self.pi_ip, self.pi_port))
        print("[Pi] Connected!")
        return s

    def send_player_id_to_pi(self, pi_socket: socket.socket, player_id: int, role: str):
        msg = {"action": "assign_player_id", "player_id": player_id}
        pi_socket.send(json.dumps(msg).encode())
        print(f"[Pi] Sent player ID {player_id} to Raspberry Pi")

    def setup(self) -> cv2.VideoCapture:
        """
        sets up the camera, assigns number to every person
        """

        os_name = platform.system()

        if os_name == "Windows":
            num = 0
            backend = cv2.CAP_DSHOW 
        else:
            num = 1
            backend = cv2.CAP_AVFOUNDATION

        print(f"[Camera] Detected OS: {os_name}, using backend: {backend}")

        cap = cv2.VideoCapture(num, backend) ## TEST: AVFOUNDATION MIGHT ONLY WORK FOR MACS
        time.sleep(1)  # give the camera time to initialize
        if not cap.isOpened():
            print("Cannot open camera")
            exit()
        return cap


    def detect_head_position(self, RECEIVER_IP, PORT):
        """
        Detects head position (up or down) for a single person and sends
        signals to server whenever the state changes.
        No face detected = heads down
        """

        cap = self.setup()
        # Connect to server
        client = client_connect(RECEIVER_IP, PORT)
        print(f"Connected to server at {RECEIVER_IP}:{PORT}")
        
        # Send setup signal and receive player ID from server
        print("Sending setup signal to server...")
        send_json(client, -1, "setup", None)  # Use -1 as placeholder player_id
        
        # Wait for server to send back player ID
        print("Waiting for player ID from server...")
        response = receive_json(client)
        print("RESPONSE....")
        print_dic(response)
        PLAYER_ID = response.get("player", 0)
        
        print("=" * 50)
        print(f"ASSIGNED PLAYER ID: {PLAYER_ID}")
        print("=" * 50)

        response = receive_json(client)
        role = response.get("action", "None")
        if role == "mafia":
            print("YOU ARE MAFIA")
        elif role == "doctor":
            print("YOU ARE DOCTOR")
        elif role == "civilian":
            print("YOU ARE CIVILIAN")
        else:
            print("Error, no role received")
            # Connect to Raspberry Pi and send player ID
        pi_socket = self.connect_to_pi()
        self.send_player_id_to_pi(pi_socket, PLAYER_ID, role)
        pi_socket.close()  # Done for now
        
        previous_state: Optional[str] = None
        
        with mp_face.FaceMesh(
            max_num_faces=1,  # Only track one person
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as face_mesh:
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to grab frame")
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(frame_rgb)

                current_state = None
                display_text = "No face detected - Head: DOWN"

                if results.multi_face_landmarks:
                    face_landmarks = results.multi_face_landmarks[0]  # Only use first face
                    
                    h, w, _ = frame.shape
                    nose_tip = face_landmarks.landmark[NOSE]
                    chin = face_landmarks.landmark[CHIN]
                    forehead = face_landmarks.landmark[FOREHEAD]

                    nose_y = int(nose_tip.y * h)
                    chin_y = int(chin.y * h)
                    forehead_y = int(forehead.y * h)

                    head_height = chin_y - forehead_y
                    nose_pos_relative = nose_y - forehead_y

                    # Determine current head state
                    if nose_pos_relative < head_height * 0.666666:
                        current_state = "headUp"
                        display_text = "Head: UP"
                    else:
                        current_state = "headDown"
                        display_text = "Head: DOWN"
                    
                    # Draw face mesh
                    mp_drawing.draw_landmarks(
                        frame, 
                        face_landmarks, 
                        mp_face.FACEMESH_TESSELATION
                    )
                else:
                    # No face detected = heads down
                    current_state = "headDown"

                # Check if state changed
                if previous_state is not None and previous_state != current_state:
                    # State flip-flopped - send signal to server
                    send_json(client, PLAYER_ID, current_state, None)
                elif previous_state is None:
                    # First detection - send initial state
                    send_json(client, PLAYER_ID, current_state, None)

                previous_state = current_state

                # Display current state and player ID on frame
                display_with_id = f"Player {PLAYER_ID}: {display_text}"
                cv2.putText(
                    frame, 
                    display_with_id, 
                    (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1, 
                    (0, 255, 0) if current_state == "headUp" else (0, 0, 255), 
                    2
                )
                cv2.imshow("Head Position Tracker", frame)

                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("\nQuitting...")
                    break

        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
        client_close(client)
        print("Camera and connection closed")


if __name__ == "__main__":
    RECEIVER_IP = "172.16.7.4"
    PORT = 5050
    PI_IP = "RASPBERRY_PI_IP_HERE"
    PI_PORT = 5051
    pose = Pose(PI_IP, PI_PORT)
    # pose.setup()
    pose.detect_head_position(RECEIVER_IP, PORT)
