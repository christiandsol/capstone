import cv2
import time
import mediapipe as mp
from typing import List

mp_face = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

class Game:
    def __init__(self, args: List[str]):
        for i, arg in enumerate(args):
            print("Arg: ", arg)
            match arg:
                case "-n": 
                    self.numPeople = int(args[i + 1])


    def setup(self) -> cv2.VideoCapture:
        """
        sets up the camera, assigns number to every person
        """
        cap = cv2.VideoCapture(1, cv2.CAP_AVFOUNDATION)
        time.sleep(0.5)  # give the camera time to initialize
        if not cap.isOpened():
            print("Cannot open camera")
            exit()
        return cap
    def headsDown(self) -> int: 
        """
        continues until: 
        - only 1 person (mafia) has their head up and gestures who to kill
        - mafia puts their head down (everyone has heads down)
        returns: integer corresponding to player mafia voted for
        """
        cap = self.setup()
        all_down_start = None
        with mp_face.FaceMesh(max_num_faces=10, refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5) as face_mesh:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to grab frame")
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(frame_rgb)

                head_up_count = 0
                head_down_count = 0

                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        h, w, _ = frame.shape
                        nose_tip = face_landmarks.landmark[1]
                        chin = face_landmarks.landmark[152]
                        forehead = face_landmarks.landmark[10]

                        nose_y = int(nose_tip.y * h)
                        chin_y = int(chin.y * h)
                        forehead_y = int(forehead.y * h)

                        head_height = chin_y - forehead_y
                        nose_pos_relative = nose_y - forehead_y

                        if nose_pos_relative < head_height * 0.666666:
                            head_up_count += 1
                        else:
                            head_down_count += 1

                        mp_drawing.draw_landmarks(frame, face_landmarks, mp_face.FACEMESH_TESSELATION)

                total_people = head_up_count + head_down_count
                if total_people != self.numPeople:
                    display_text = f"Number of observable people doesn't match number of players. Total people being observed is: {total_people}, numPeople: {self.numPeople}"
                    all_down_start = None
                else:
                    display_text = f"Head Up: {head_up_count}  Head Down: {head_down_count}"
                    if head_down_count == self.numPeople:
                        if all_down_start is None:
                            all_down_start = time.time()
                        elif time.time() - all_down_start >= 2:
                            display_text = "Successful!"
                    else:
                        all_down_start = None

                cv2.putText(frame, display_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Camera", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        cap.release()
        cv2.destroyAllWindows()
        return 1

