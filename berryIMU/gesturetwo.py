import socket
import time
import sys
import os
from typing import List, Tuple, Optional

# Add parent directory to path so we can import util
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util import client_connect, send_json


"""
BerryIMU-based gesture voting client.

Goal:
- Player physically "draws" a digit 1–8 with the BerryIMU.
- We recognize which digit was drawn from accelerometer/gyro data.
- We then send a vote signal to the Mafia server:
    {
        "player": <player_id>,
        "action": "vote",
        "target": <1-8>
    }
    
Directions:
- 1: Up
- 2: Right
- 3: Down
- 4: Left
- 5: Up-Left (diagonal)
- 6: Up-Right (diagonal)
- 7: Down-Left (diagonal)
- 8: Down-Right (diagonal)

This file is written as a guided template:
- The network / vote sending logic is implemented.
- IMU-specific parts are stubbed with clear TODOs for you to fill using the
  BerryIMU library you are using on the Raspberry Pi.
"""


class BerryIMUInterface:
    """
    Thin wrapper around the BerryIMU.

    This implementation tries common BerryIMU function names.
    Adjust the import and function names to match your specific BerryIMU library.
    """

    def __init__(self, debug: bool = False):
        """
        Initialize the BerryIMU using the IMU module (same as berryIMY.py).

        Args:
            debug: If True, print each sample as it's read (useful for calibration).
        """
        self.debug = debug
        
        # Try to import and initialize IMU module (same approach as berryIMY.py)
        try:
            import IMU
            
            print("[BerryIMU] Attempting to detect IMU...")
            # Detect if BerryIMU is connected
            IMU.detectIMU()
            if IMU.BerryIMUversion == 99:
                print("[BerryIMU] ERROR: No BerryIMU found... exiting")
                self.IMU = None
                return
            
            print(f"[BerryIMU] Detected version {IMU.BerryIMUversion}, initializing...")
            # Initialize the accelerometer, gyroscope and compass
            IMU.initIMU()
            
            self.IMU = IMU
            print(f"[BerryIMU] Initialized successfully (version {IMU.BerryIMUversion})")
            
        except ImportError as e:
            print(f"[BerryIMU] WARNING: Could not import IMU library: {e}")
            print("[BerryIMU] Please make sure the IMU.py module is in your Python path.")
            print("[BerryIMU] For now, using dummy values for testing.")
            self.IMU = None
        except PermissionError as e:
            print(f"[BerryIMU] ERROR: Permission denied accessing I2C bus: {e}")
            print("[BerryIMU] Try running with: sudo python3 gesture.py test")
            print("[BerryIMU] Or add your user to the i2c group: sudo usermod -a -G i2c $USER")
            self.IMU = None
        except OSError as e:
            print(f"[BerryIMU] ERROR: I2C bus access error: {e}")
            print("[BerryIMU] Check if I2C is enabled: sudo raspi-config -> Interface Options -> I2C -> Enable")
            print("[BerryIMU] Check hardware connections and power supply.")
            self.IMU = None
        except Exception as e:
            print(f"[BerryIMU] WARNING: Could not initialize BerryIMU: {e}")
            print(f"[BerryIMU] Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self.IMU = None

    def read_sample(self) -> Tuple[float, float, float, float, float, float]:
        """
        Read one IMU sample.

        Returns:
            (ax, ay, az, gx, gy, gz)
            where:
              - a* are accelerometer readings (raw values, typically in g or scaled units)
              - g* are gyro readings (raw values, typically in deg/s or scaled units)

        NOTE: For gesture recognition, we need RAW accelerometer/gyro values,
        not angles. If your library only provides angles, we can work with those
        but it's less ideal. Adjust the function names below to match your library.
        """
        if self.IMU is None:
            # Dummy values for testing when library isn't available
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Read raw accelerometer and gyroscope values from IMU module
        # (same approach as berryIMY.py - we use raw values, not angles)
        try:
            ax = self.IMU.readACCx()
            ay = self.IMU.readACCy()
            az = self.IMU.readACCz()
            gx = self.IMU.readGYRx()
            gy = self.IMU.readGYRy()
            gz = self.IMU.readGYRz()
            
        except AttributeError as e:
            print(f"[BerryIMU] ERROR: Function not found. {e}")
            print("[BerryIMU] Please check your IMU module for correct function names.")
            print("[BerryIMU] Returning dummy values (0,0,0,0,0,0)")
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        except Exception as e:
            print(f"[BerryIMU] ERROR reading sensor: {e}")
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        sample = (ax, ay, az, gx, gy, gz)
        
        if self.debug:
            print(f"[IMU] ax={ax:8.2f}, ay={ay:8.2f}, az={az:8.2f}, "
                  f"gx={gx:8.2f}, gy={gy:8.2f}, gz={gz:8.2f}")
        
        return sample


class GestureRecognizer:
    """
    Takes short sequences of IMU samples and classifies them
    as digits 1–8 (4 cardinal directions + 4 diagonal directions).

    Simple heuristic-based approach:
        - Detects movement direction using accelerometer data
        - Recognizes 8 directions: Up, Down, Left, Right, and 4 diagonals
    """

    def __init__(self):
        pass

    def classify(self, samples: List[Tuple[float, float, float, float, float, float]]) -> Optional[int]:
        """
        Classify a sequence of IMU samples as a digit 1–8.

        Args:
            samples: list of (ax, ay, az, gx, gy, gz) over time.

        Returns:
            1-8 if confidently recognized, or None if unclear.
            
        Gesture mapping:
            - Digit 1: Up
            - Digit 2: Right
            - Digit 3: Down
            - Digit 4: Left
            - Digit 5: Up-Left (diagonal)
            - Digit 6: Up-Right (diagonal)
            - Digit 7: Down-Left (diagonal)
            - Digit 8: Down-Right (diagonal)
        """
        if not samples:
            return None

        # Calculate motion by looking at the RANGE (max - min) of each axis
        ax_values = [s[0] for s in samples]
        ay_values = [s[1] for s in samples]
        
        # Calculate range (movement magnitude) for each axis
        ax_range = max(ax_values) - min(ax_values)
        ay_range = max(ay_values) - min(ay_values)
        
        # Calculate average change direction
        mean_ax = sum(ax_values) / len(ax_values)
        mean_ay = sum(ay_values) / len(ay_values)
        
        # Get baseline (first few samples) to detect change from rest
        baseline_samples = min(5, len(samples) // 4)
        baseline_ax = sum(ax_values[:baseline_samples]) / baseline_samples
        baseline_ay = sum(ay_values[:baseline_samples]) / baseline_samples
        
        # Calculate change from baseline
        delta_ax = mean_ax - baseline_ax
        delta_ay = mean_ay - baseline_ay

        # Threshold for significant movement
        min_movement = 200.0  # Minimum range to consider it a gesture
        min_diagonal_movement = 150.0  # Lower threshold for diagonal (both axes need movement)

        # Check if there's significant movement
        max_range = max(ax_range, ay_range)
        if max_range < min_movement:
            return None

        # Threshold for direction detection
        direction_threshold = 100.0  # Minimum delta to consider a direction
        diagonal_threshold = 70.0  # Lower threshold for diagonal detection

        # Check for diagonal movements first (both axes have significant movement)
        # Diagonal movements require both axes to show movement
        if ax_range >= min_diagonal_movement and ay_range >= min_diagonal_movement:
            # Both axes have significant movement - check for diagonal
            
            # Up-Right: both positive
            if delta_ay > diagonal_threshold and delta_ax > diagonal_threshold:
                return 6
            
            # Up-Left: ay positive, ax negative
            elif delta_ay > diagonal_threshold and delta_ax < -diagonal_threshold:
                return 5
            
            # Down-Right: ay negative, ax positive
            elif delta_ay < -diagonal_threshold and delta_ax > diagonal_threshold:
                return 8
            
            # Down-Left: both negative
            elif delta_ay < -diagonal_threshold and delta_ax < -diagonal_threshold:
                return 7

        # If not diagonal, check for cardinal directions
        # Dominant vertical movement (up/down)
        if ay_range >= ax_range:
            if delta_ay > direction_threshold:  # Upward
                return 1
            elif delta_ay < -direction_threshold:  # Downward
                return 3
            else:
                return None  # Not clear enough

        # Dominant horizontal movement (left/right)
        else:  # ax_range > ay_range
            if delta_ax > direction_threshold:  # Rightward
                return 2
            elif delta_ax < -direction_threshold:  # Leftward
                return 4
            else:
                return None  # Not clear enough

        # Fallback: nothing recognized
        return None


class GestureVotingClient:
    """
    Runs on the Raspberry Pi:
        - Reads IMU data from BerryIMU.
        - When the player "draws" a digit 1–8, recognizes it.
        - Sends a 'vote' signal to the Mafia game server.
    """

    def __init__(self, server_ip: str, server_port: int, player_id: int, debug_imu: bool = False):
        self.server_ip = server_ip
        self.server_port = server_port
        self.player_id = player_id

        self.imu = BerryIMUInterface(debug=debug_imu)
        self.recognizer = GestureRecognizer()

    def _record_gesture_sequence(self, duration_s: float = 1.0, sample_rate_hz: float = 50.0, debug: bool = False) -> List[
        Tuple[float, float, float, float, float, float]
    ]:
        """
        Record a short IMU sequence while the player is drawing a digit.

        For now, this simply samples the IMU for a fixed duration.
        Later you can:
            - Use a button press to mark start/end.
            - Use a motion threshold to auto-detect start.
        
        Args:
            duration_s: How long to record (seconds).
            sample_rate_hz: Sampling rate (samples per second).
            debug: If True, print each sample as it's recorded.
        """
        samples: List[Tuple[float, float, float, float, float, float]] = []
        dt = 1.0 / sample_rate_hz
        num_samples = int(duration_s * sample_rate_hz)

        print(f"[Recording] Collecting {num_samples} samples over {duration_s}s...")
        
        for i in range(num_samples):
            sample = self.imu.read_sample()
            samples.append(sample)
            
            if debug and i % 10 == 0:  # Print every 10th sample to avoid spam
                print(f"  Sample {i}: ax={sample[0]:.2f}, ay={sample[1]:.2f}, az={sample[2]:.2f}, "
                      f"gx={sample[3]:.2f}, gy={sample[4]:.2f}, gz={sample[5]:.2f}")
            
            time.sleep(dt)

        return samples

    def send_vote(self, target_player: int):
        """
        Connect to the server and send a single 'vote' action.
        If server is not available, prints what would be sent instead.
        """
        try:
            client = client_connect(self.server_ip, self.server_port)
            send_json(client, self.player_id, "vote", target_player)
            client.close()
            print(f"[Gesture] Sent vote: player {self.player_id} -> target {target_player}")
        except (ConnectionRefusedError, OSError) as e:
            # Server not running - just print what would be sent
            vote_message = {
                "player": self.player_id,
                "action": "vote",
                "target": target_player
            }
            print(f"[Gesture] Server not available (connection error: {e})")
            print(f"[Gesture] Would send: {vote_message}")
            print(f"[Gesture] JSON format: {{\"player\": {self.player_id}, \"action\": \"vote\", \"target\": {target_player}}}")

    def run_interactive(self):
        """
        Simple interactive loop for testing:
            - Wait for user to press Enter to start a gesture.
            - Record a short IMU sequence.
            - Classify it as digit 1–8.
            - If recognized, send vote to server.
        """
        print("=== Gesture Voting Client (Digits 1-8) ===")
        print(f"Player ID: {self.player_id}")
        print("When it's time to vote, draw a gesture (digit 1–8) with the BerryIMU.")
        print("Directions: 1=Up, 2=Right, 3=Down, 4=Left, 5=Up-Left, 6=Up-Right, 7=Down-Left, 8=Down-Right")
        print("Press Enter to record a gesture, or 'q' + Enter to quit.")

        while True:
            cmd = input("\nReady to record gesture (Enter to start, 'q' to quit): ").strip().lower()
            if cmd == "q":
                print("Exiting gesture client.")
                break

            print("Recording gesture... move the BerryIMU now.")
            # First time: enable debug to see raw values
            debug_mode = input("Enable debug mode to see raw IMU values? (y/n, default=n): ").strip().lower() == "y"
            samples = self._record_gesture_sequence(duration_s=1.0, sample_rate_hz=50.0, debug=debug_mode)
            print("Recording complete, recognizing...")
            
            # Print summary of collected data
            if samples:
                avg_ax = sum(s[0] for s in samples) / len(samples)
                avg_ay = sum(s[1] for s in samples) / len(samples)
                avg_az = sum(s[2] for s in samples) / len(samples)
                print(f"[Summary] Average accel: ax={avg_ax:.2f}, ay={avg_ay:.2f}, az={avg_az:.2f}")

            digit = self.recognizer.classify(samples)
            if digit is None:
                print("Could not confidently recognize a digit. Try again.")
                continue

            if digit not in range(1, 9):
                print(f"Recognized digit {digit}, but only 1–8 are valid targets. Ignoring.")
                continue

            print(f"Recognized gesture as digit {digit} (vote for player {digit}).")

            # Confirm with the player before sending, to avoid accidental votes.
            confirm = input(f"Send vote for player {digit}? (y/n): ").strip().lower()
            if confirm == "y":
                self.send_vote(digit)
            else:
                print("Vote cancelled, try again.")


def test_imu_readings():
    """
    Simple test function to just read and print IMU values continuously.
    Run this first to verify your BerryIMU is working before trying gesture recognition.
    """
    print("=== BerryIMU Test Mode ===")
    print("This will continuously read and print IMU values.")
    print("Press Ctrl+C to stop.\n")
    
    imu = BerryIMUInterface(debug=True)
    
    try:
        while True:
            sample = imu.read_sample()
            print(f"ax={sample[0]:8.2f}, ay={sample[1]:8.2f}, az={sample[2]:8.2f}, "
                  f"gx={sample[3]:8.2f}, gy={sample[4]:8.2f}, gz={sample[5]:8.2f}")
            time.sleep(0.1)  # 10 Hz for readability
    except KeyboardInterrupt:
        print("\n[Test] Stopped.")


if __name__ == "__main__":
    import sys
    
    # Check if user wants to run in test mode (just print IMU values)
    # if len(sys.argv) > 1 and sys.argv[1] == "test":
    #     test_imu_readings()
    #     sys.exit(0)
    
    # TODO: Set these to your actual server IP / port and player ID.
    SERVER_IP = "172.16.7.4"  # Example: laptop/server IP
    SERVER_PORT = 5050

    # For now, hard-code player ID or pass via command line argument.
    # Later, you can integrate with your existing player-ID-assignment flow.
    PLAYER_ID = 1

    # Enable IMU debug mode by default for first-time setup
    DEBUG_IMU = True
    
    print("=== Gesture Voting Client ===")
    print("To test IMU readings only, run: python3 gesture.py test")
    print()

    client = GestureVotingClient(SERVER_IP, SERVER_PORT, PLAYER_ID, debug_imu=DEBUG_IMU)
    client.run_interactive()


