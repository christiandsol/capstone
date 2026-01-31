import socket
import time
import sys
import os
import math
import pickle
from typing import List, Tuple, Optional, Dict

# numpy is required for efficient array operations
try:
    import numpy as np
except ImportError:
    print("ERROR: numpy is required. Install it with: pip install numpy")
    sys.exit(1)

# Add parent directory to path so we can import util
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util import client_connect, send_json


"""
Gyroscope-based gesture recognition for digits 1-8.

This implementation uses GYROSCOPE data as the primary source for trajectory tracking.
It integrates angular velocity to get rotation angles, which better captures the
shape of gestures drawn on flat surfaces.
"""


class BerryIMUInterface:
    """
    Thin wrapper around the BerryIMU.
    Same as original gesture.py - reads raw accelerometer and gyroscope data.
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        
        try:
            import IMU
            
            IMU.detectIMU()
            if IMU.BerryIMUversion == 99:
                print("[BerryIMU] ERROR: No BerryIMU found... exiting")
                self.IMU = None
                return
            
            IMU.initIMU()
            self.IMU = IMU
            
        except ImportError as e:
            print(f"[BerryIMU] WARNING: Could not import IMU library: {e}")
            self.IMU = None
        except PermissionError as e:
            print(f"[BerryIMU] ERROR: Permission denied accessing I2C bus: {e}")
            self.IMU = None
        except OSError as e:
            print(f"[BerryIMU] ERROR: I2C bus access error: {e}")
            self.IMU = None
        except Exception as e:
            print(f"[BerryIMU] WARNING: Could not initialize BerryIMU: {e}")
            self.IMU = None

    def read_sample(self) -> Tuple[float, float, float, float, float, float]:
        """
        Read one IMU sample.
        Returns: (ax, ay, az, gx, gy, gz)
        """
        if self.IMU is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        try:
            ax = self.IMU.readACCx()
            ay = self.IMU.readACCy()
            az = self.IMU.readACCz()
            gx = self.IMU.readGYRx()
            gy = self.IMU.readGYRy()
            gz = self.IMU.readGYRz()
        except Exception as e:
            if self.debug:
                print(f"[BerryIMU] ERROR reading sensor: {e}")
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        
        return (ax, ay, az, gx, gy, gz)


class GyroTrajectoryTracker:
    """
    Tracks the 3D rotation trajectory of the gesture by integrating gyroscope data.
    Uses angular velocity (deg/s) to compute rotation angles (degrees).
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset trajectory state."""
        # Rotation angles in degrees (integrated from angular velocity)
        self.rotation = np.array([0.0, 0.0, 0.0])  # rx, ry, rz (rotation around x, y, z axes)
        self.trajectory = []
    
    def process_samples(self, samples: List[Tuple[float, float, float, float, float, float]], 
                       dt: float = 0.02) -> List[Tuple[float, float, float]]:
        """
        Process IMU samples to extract rotation trajectory from gyroscope.
        
        Args:
            samples: List of (ax, ay, az, gx, gy, gz) tuples
            dt: Time step between samples (default 0.02s for 50Hz)
        
        Returns:
            List of (rx, ry, rz) rotation angles in degrees
        """
        self.reset()
        rotations = []
        
        # Remove baseline (drift/bias) using first few samples (assuming device is at rest initially)
        if len(samples) >= 3:
            baseline_gx = sum(s[3] for s in samples[:3]) / 3
            baseline_gy = sum(s[4] for s in samples[:3]) / 3
            baseline_gz = sum(s[5] for s in samples[:3]) / 3
        else:
            baseline_gx = baseline_gy = baseline_gz = 0.0
        
        for sample in samples:
            ax, ay, az, gx, gy, gz = sample
            
            # Remove baseline (gyroscope bias/drift)
            gx_clean = gx - baseline_gx
            gy_clean = gy - baseline_gy
            gz_clean = gz - baseline_gz
            
            # Integrate angular velocity to get rotation angle (simple Euler integration)
            # Angular velocity is typically in deg/s, so multiply by dt to get degrees
            self.rotation[0] += gx_clean * dt
            self.rotation[1] += gy_clean * dt
            self.rotation[2] += gz_clean * dt
            
            rotations.append(tuple(self.rotation.copy()))
        
        return rotations


class GestureFeatureExtractor:
    """
    Extracts features from gyroscope-based rotation trajectories to help classify digits 1-8.
    """
    
    @staticmethod
    def extract_features(rotations: List[Tuple[float, float, float]], 
                        samples: List[Tuple[float, float, float, float, float, float]]) -> Dict[str, float]:
        """
        Extract features from a rotation trajectory.
        
        Returns a dictionary of features useful for digit classification.
        """
        if len(rotations) < 3:
            return {}
        
        features = {}
        
        # Convert to numpy arrays for easier computation
        rot_array = np.array(rotations)
        gyro_data = np.array([[s[3], s[4], s[5]] for s in samples])
        accel_data = np.array([[s[0], s[1], s[2]] for s in samples])
        
        # 1. Number of direction changes (sharp rotation changes)
        direction_changes = 0
        if len(rot_array) > 2:
            for i in range(1, len(rot_array) - 1):
                v1 = rot_array[i] - rot_array[i-1]
                v2 = rot_array[i+1] - rot_array[i]
                if np.linalg.norm(v1) > 0.1 and np.linalg.norm(v2) > 0.1:
                    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
                    cos_angle = np.clip(cos_angle, -1.0, 1.0)
                    angle = math.acos(cos_angle)
                    if angle > math.pi / 3:  # More than 60 degrees
                        direction_changes += 1
        features['direction_changes'] = direction_changes
        
        # 2. Total rotation path length
        path_length = 0.0
        for i in range(1, len(rot_array)):
            path_length += np.linalg.norm(rot_array[i] - rot_array[i-1])
        features['path_length'] = path_length
        
        # 3. Straightness (ratio of straight-line rotation to total rotation path)
        if path_length > 0:
            straight_dist = np.linalg.norm(rot_array[-1] - rot_array[0])
            features['straightness'] = straight_dist / path_length
        else:
            features['straightness'] = 0.0
        
        # 4. Loop detection (for digits like 6, 8, 0)
        # Check if rotation trajectory returns close to start
        if len(rot_array) > 10:
            start_rot = rot_array[0]
            min_dist_to_start = float('inf')
            for i in range(len(rot_array) // 2, len(rot_array)):
                dist = np.linalg.norm(rot_array[i] - start_rot)
                min_dist_to_start = min(min_dist_to_start, dist)
            features['loop_score'] = 1.0 / (1.0 + min_dist_to_start)  # Higher if returns close to start
        else:
            features['loop_score'] = 0.0
        
        # 5. Dominant rotation axis (which axis has most rotation)
        ranges = {
            'x': np.max(rot_array[:, 0]) - np.min(rot_array[:, 0]),
            'y': np.max(rot_array[:, 1]) - np.min(rot_array[:, 1]),
            'z': np.max(rot_array[:, 2]) - np.min(rot_array[:, 2])
        }
        features['dominant_axis'] = max(ranges, key=ranges.get)
        
        # 6. Average gyroscope rotation magnitude
        gyro_magnitude = np.mean(np.linalg.norm(gyro_data, axis=1))
        features['gyro_rotation'] = gyro_magnitude
        
        # 7. Number of peaks in gyroscope magnitude (indicates rotation strokes)
        gyro_magnitude = np.linalg.norm(gyro_data, axis=1)
        if len(gyro_magnitude) > 3:
            threshold = np.mean(gyro_magnitude) + 0.5 * np.std(gyro_magnitude)
            peaks = sum(1 for i in range(1, len(gyro_magnitude) - 1) 
                       if gyro_magnitude[i] > threshold and 
                       gyro_magnitude[i] > gyro_magnitude[i-1] and 
                       gyro_magnitude[i] > gyro_magnitude[i+1])
            features['gyro_peaks'] = peaks
        else:
            features['gyro_peaks'] = 0
        
        # 8. Vertical vs horizontal rotation ratio
        vertical_range = np.max(rot_array[:, 1]) - np.min(rot_array[:, 1])  # Y-axis rotation
        horizontal_range = np.max(rot_array[:, 0]) - np.min(rot_array[:, 0])  # X-axis rotation
        if horizontal_range > 0:
            features['vertical_horizontal_ratio'] = vertical_range / horizontal_range
        else:
            features['vertical_horizontal_ratio'] = 100.0 if vertical_range > 0 else 0.0
        
        return features


class DTWMatcher:
    """
    Simple Dynamic Time Warping implementation for template matching.
    """
    
    @staticmethod
    def dtw_distance(seq1: np.ndarray, seq2: np.ndarray) -> float:
        """
        Compute DTW distance between two sequences.
        
        Args:
            seq1, seq2: Numpy arrays of shape (n, d) where n is length and d is dimension
        
        Returns:
            DTW distance (lower is more similar)
        """
        n, m = len(seq1), len(seq2)
        
        # Initialize cost matrix
        dtw = np.full((n + 1, m + 1), float('inf'))
        dtw[0, 0] = 0.0
        
        # Compute DTW
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = np.linalg.norm(seq1[i-1] - seq2[j-1])
                dtw[i, j] = cost + min(dtw[i-1, j],      # insertion
                                       dtw[i, j-1],      # deletion
                                       dtw[i-1, j-1])    # match
        
        return dtw[n, m]
    
    @staticmethod
    def normalize_sequence(seq: np.ndarray) -> np.ndarray:
        """
        Normalize sequence to be translation and scale invariant.
        """
        if len(seq) == 0:
            return seq
        
        # Center the sequence
        seq = seq - np.mean(seq, axis=0)
        
        # Scale to unit size
        max_range = np.max(np.abs(seq))
        if max_range > 0:
            seq = seq / max_range
        
        return seq


class GyroGestureRecognizer:
    """
    Recognizes digits 1-8 from gyroscope-based gesture data.
    Uses rotation trajectory tracking, feature extraction, and template matching.
    """
    
    # Template file path (stores templates in the same directory as this script)
    TEMPLATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gyro_gesture_templates.pkl')
    
    def __init__(self, template_file: Optional[str] = None, debug: bool = False):
        self.tracker = GyroTrajectoryTracker()
        self.feature_extractor = GestureFeatureExtractor()
        self.dtw_matcher = DTWMatcher()
        self.debug = debug
        
        # Use custom template file path if provided, otherwise use default
        self.template_file = template_file if template_file else self.TEMPLATE_FILE
        
        # Store templates for each digit (can be populated with training data)
        self.templates: Dict[int, List[np.ndarray]] = {
            1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []
        }
        
        # Load existing templates from file (if they exist)
        self.load_templates()
        
        # Feature-based classification rules (heuristic approach)
        # These can be refined with actual data
        self.digit_features = {
            1: {'direction_changes': (0, 1), 'straightness': (0.8, 1.0), 'vertical_horizontal_ratio': (1.5, 100), 'gyro_peaks': (0, 15)},
            2: {'direction_changes': (1, 3), 'straightness': (0.3, 0.8), 'vertical_horizontal_ratio': (0.3, 1.5)},
            3: {'direction_changes': (0, 4), 'straightness': (0.2, 0.95), 'vertical_horizontal_ratio': (0.5, 3.0), 'gyro_peaks': (5, 25)},
            4: {'direction_changes': (0, 3), 'straightness': (0.4, 0.75), 'vertical_horizontal_ratio': (0.4, 1.2), 'gyro_peaks': (15, 30)},
            5: {'direction_changes': (2, 5), 'straightness': (0.2, 0.7), 'vertical_horizontal_ratio': (0.5, 2.0)},
            6: {'direction_changes': (0, 2), 'loop_score': (0.3, 1.0), 'straightness': (0.0, 0.5)},
            7: {'direction_changes': (1, 3), 'straightness': (0.4, 0.9), 'vertical_horizontal_ratio': (0.3, 1.5)},
            8: {'direction_changes': (0, 1), 'loop_score': (0.5, 1.0), 'gyro_rotation': (100, 500), 'path_length': (0.5, 3.0)}
        }
    
    def load_templates(self):
        """
        Load templates from file if it exists.
        Templates are stored as a dictionary mapping digits (1-8) to lists of normalized rotation trajectories.
        """
        if os.path.exists(self.template_file):
            try:
                with open(self.template_file, 'rb') as f:
                    loaded_templates = pickle.load(f)
                    # Validate and load templates
                    for digit in range(1, 9):
                        if digit in loaded_templates and isinstance(loaded_templates[digit], list):
                            self.templates[digit] = loaded_templates[digit]
                    print(f"[GyroGesture] Loaded templates from {self.template_file}")
                    # Print summary
                    total_templates = sum(len(templates) for templates in self.templates.values())
                    print(f"[GyroGesture] Loaded {total_templates} templates: {[f'{d}:{len(self.templates[d])}' for d in range(1, 9)]}")
            except Exception as e:
                print(f"[GyroGesture] WARNING: Could not load templates from {self.template_file}: {e}")
                print("[GyroGesture] Starting with empty templates.")
        else:
            print(f"[GyroGesture] No template file found at {self.template_file}")
            print("[GyroGesture] Starting with empty templates. Train templates with 't <digit>' command.")
    
    def save_templates(self):
        """
        Save current templates to file.
        Templates are saved as a pickle file for persistence across program restarts.
        """
        try:
            with open(self.template_file, 'wb') as f:
                pickle.dump(self.templates, f)
            total_templates = sum(len(templates) for templates in self.templates.values())
            print(f"[GyroGesture] Saved {total_templates} templates to {self.template_file}")
        except Exception as e:
            print(f"[GyroGesture] ERROR: Could not save templates to {self.template_file}: {e}")
    
    def add_template(self, digit: int, samples: List[Tuple[float, float, float, float, float, float]]):
        """
        Add a template gesture for a specific digit.
        Useful for training/calibration.
        Automatically saves templates to file after adding.
        """
        if digit not in range(1, 9):
            return
        
        dt = 0.02  # 50Hz
        rotations = self.tracker.process_samples(samples, dt)
        if len(rotations) > 0:
            rot_array = np.array(rotations)
            normalized = self.dtw_matcher.normalize_sequence(rot_array)
            self.templates[digit].append(normalized)
            # Automatically save templates after adding a new one
            self.save_templates()
    
    def classify(self, samples: List[Tuple[float, float, float, float, float, float]]) -> Optional[int]:
        """
        Classify a sequence of IMU samples as a digit 1-8.
        
        Uses a combination of:
        1. Template matching (if templates are available)
        2. Feature-based classification (heuristic rules)
        """
        if not samples or len(samples) < 10:
            return None
        
        # Check minimum movement threshold using gyroscope
        gyro_magnitudes = [math.sqrt(s[3]**2 + s[4]**2 + s[5]**2) for s in samples]
        max_gyro = max(gyro_magnitudes)
        min_gyro = min(gyro_magnitudes)
        if max_gyro - min_gyro < 50:  # Too little rotation
            return None
        
        # Extract rotation trajectory from gyroscope
        dt = 0.02  # 50Hz
        rotations = self.tracker.process_samples(samples, dt)
        
        if len(rotations) < 5:
            return None
        
        # Extract features
        features = self.feature_extractor.extract_features(rotations, samples)
        
        if self.debug:
            print(f"\n[Debug] ========== RECOGNITION ANALYSIS ==========")
            print(f"[Debug] Extracted features:")
            for feat_name, feat_value in features.items():
                if isinstance(feat_value, (int, float)):
                    print(f"[Debug]   {feat_name}: {feat_value:.4f}")
                else:
                    print(f"[Debug]   {feat_name}: {feat_value}")
            print(f"[Debug] ===========================================\n")
        
        # Try template matching first (if templates exist)
        template_match_used = False
        if any(len(templates) > 0 for templates in self.templates.values()):
            rot_array = np.array(rotations)
            normalized_input = self.dtw_matcher.normalize_sequence(rot_array)
            
            best_match = None
            best_score = float('inf')
            all_distances = {}
            
            for digit in range(1, 9):
                if len(self.templates[digit]) > 0:
                    min_dist_for_digit = float('inf')
                    for template in self.templates[digit]:
                        distance = self.dtw_matcher.dtw_distance(normalized_input, template)
                        min_dist_for_digit = min(min_dist_for_digit, distance)
                        if distance < best_score:
                            best_score = distance
                            best_match = digit
                    all_distances[digit] = min_dist_for_digit
            
            if self.debug:
                print(f"\n[Debug] ========== TEMPLATE MATCHING ==========")
                print(f"[Debug] Template distances for each digit:")
                for d in sorted(all_distances.keys()):
                    marker = " <-- BEST" if d == best_match else ""
                    print(f"[Debug]   Digit {d}: {all_distances[d]:.2f}{marker}")
                print(f"[Debug] Best template match: digit {best_match} with distance {best_score:.2f}")
                print(f"[Debug] Threshold: {best_score:.2f} < 150.0? {best_score < 150.0}")
                print(f"[Debug] ========================================\n")
            
            # Template matching threshold - higher = more lenient
            # Increased to 150.0 to allow templates to match even with some variation
            if best_match and best_score < 150.0:
                # Check if best match is significantly better than second best
                # If distances are too close, the match isn't confident
                if len(all_distances) > 1:
                    sorted_distances = sorted(all_distances.values())
                    second_best_distance = sorted_distances[1] if len(sorted_distances) > 1 else float('inf')
                    distance_difference = second_best_distance - best_score
                    distance_ratio = best_score / second_best_distance if second_best_distance > 0 else 1.0
                    
                    if self.debug:
                        print(f"[Debug] Confidence check:")
                        print(f"[Debug]   Second best distance: {second_best_distance:.2f}")
                        print(f"[Debug]   Distance difference: {distance_difference:.2f} (need > 10.0)")
                        print(f"[Debug]   Distance ratio: {distance_ratio:.2f} (need < 0.80)")
                        print(f"[Debug]   Ratio check: {distance_ratio < 0.80}")
                        print(f"[Debug]   Difference check: {distance_difference > 10.0}")
                    
                    # Require at least 20% better (ratio < 0.80) AND at least 10 points difference
                    # Stricter requirements to prevent false matches
                    confidence_passed = (distance_ratio < 0.80) and (distance_difference > 10.0)
                    
                    if self.debug:
                        print(f"[Debug] Confidence requirements:")
                        print(f"[Debug]   Ratio < 0.80? {distance_ratio < 0.80} (actual: {distance_ratio:.3f})")
                        print(f"[Debug]   Difference > 10.0? {distance_difference > 10.0} (actual: {distance_difference:.2f})")
                        print(f"[Debug]   Both conditions met? {confidence_passed}")
                    
                    if confidence_passed:
                        if self.debug:
                            print(f"[Debug] ✓ ACCEPTED: Using template match: digit {best_match} (confident match)")
                        template_match_used = True
                        return best_match
                    else:
                        if self.debug:
                            print(f"[Debug] ✗ REJECTED: Template match not confident enough")
                            if distance_ratio >= 0.80:
                                print(f"[Debug]   Ratio {distance_ratio:.3f} >= 0.80 (too close)")
                            if distance_difference <= 10.0:
                                print(f"[Debug]   Difference {distance_difference:.2f} <= 10.0 (too small)")
                            print(f"[Debug]   Falling back to feature-based classification")
                else:
                    # Only one template exists, use it if below threshold
                    if self.debug:
                        print(f"[Debug] Using template match: digit {best_match} (only template available)")
                    template_match_used = True
                    return best_match
            elif self.debug:
                print(f"[Debug] Template match rejected (distance {best_score:.2f} >= 150.0), using feature-based")
        
        # Fall back to feature-based classification
        scores = {}
        for digit in range(1, 9):
            score = 0.0
            digit_rules = self.digit_features.get(digit, {})
            matched_features = []
            
            for feature_name, (min_val, max_val) in digit_rules.items():
                if feature_name in features:
                    value = features[feature_name]
                    if min_val <= value <= max_val:
                        score += 1.0
                        matched_features.append(feature_name)
                    else:
                        # Penalize if far from expected range (less penalty than before)
                        if value < min_val:
                            penalty = abs(value - min_val) / (min_val + 1) * 0.5
                            score -= penalty
                        else:
                            penalty = abs(value - max_val) / (max_val + 1) * 0.5
                            score -= penalty
            
            scores[digit] = score
            if self.debug:
                print(f"\n[Debug] --- Digit {digit} Analysis ---")
                print(f"[Debug]   Final score: {score:.2f}")
                print(f"[Debug]   Matched features: {matched_features}")
                # Show detailed feature matching
                digit_rules = self.digit_features.get(digit, {})
                for feature_name, (min_val, max_val) in digit_rules.items():
                    if feature_name in features:
                        value = features[feature_name]
                        if min_val <= value <= max_val:
                            print(f"[Debug]   ✓ {feature_name}: {value:.4f} (expected {min_val:.2f}-{max_val:.2f}) MATCH")
                        else:
                            if value < min_val:
                                penalty = abs(value - min_val) / (min_val + 1) * 0.5
                                print(f"[Debug]   ✗ {feature_name}: {value:.4f} (expected {min_val:.2f}-{max_val:.2f}) TOO LOW, penalty: {penalty:.4f}")
                            else:
                                penalty = abs(value - max_val) / (max_val + 1) * 0.5
                                print(f"[Debug]   ✗ {feature_name}: {value:.4f} (expected {min_val:.2f}-{max_val:.2f}) TOO HIGH, penalty: {penalty:.4f}")
                    else:
                        print(f"[Debug]   ? {feature_name}: NOT AVAILABLE (expected {min_val:.2f}-{max_val:.2f})")
        
        # Find best match
        if scores:
            best_digit = max(scores, key=scores.get)
            best_score = scores[best_digit]
            second_best_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
            
            if self.debug:
                print(f"\n[Debug] ========== FEATURE-BASED RESULTS ==========")
                print(f"[Debug] All digit scores:")
                for d in sorted(scores.keys()):
                    marker = " <-- BEST" if d == best_digit else " <-- SECOND" if scores[d] == second_best_score else ""
                    print(f"[Debug]   Digit {d}: {scores[d]:.4f}{marker}")
                print(f"[Debug] Best: digit {best_digit} with score {best_score:.2f}")
                print(f"[Debug] Second best: {second_best_score:.2f}")
                score_difference = best_score - second_best_score
                print(f"[Debug] Score difference: {score_difference:.2f}")
                print(f"[Debug] Threshold check: score > 1.0? {best_score > 1.0}, difference > 0.5? {score_difference > 0.5}")
                print(f"[Debug] ===========================================\n")
            
            # Confidence threshold - need at least 1.0 points AND clear winner
            # Also require that best is significantly better than second best
            score_difference = best_score - second_best_score
            if best_score > 1.0 and score_difference > 0.5:
                if self.debug:
                    print(f"[Debug] ✓ ACCEPTED: Using feature-based match: digit {best_digit}")
                return best_digit
            elif self.debug:
                if best_score <= 1.0:
                    print(f"[Debug] ✗ REJECTED: Best score {best_score:.2f} <= 1.0 (too low)")
                if score_difference <= 0.5:
                    print(f"[Debug] ✗ REJECTED: Score difference {score_difference:.2f} <= 0.5 (too close to second best)")
        
        if self.debug:
            print("[Debug] No confident match found, returning None")
        return None


class GestureVotingClient:
    """
    Gyroscope-based gesture voting client that supports digits 1-8.
    """
    
    def __init__(self, server_ip: str, server_port: int, player_id: int, debug_imu: bool = False, debug_recognition: bool = False):
        self.server_ip = server_ip
        self.server_port = server_port
        self.player_id = player_id
        
        self.imu = BerryIMUInterface(debug=debug_imu)
        self.recognizer = GyroGestureRecognizer(debug=debug_recognition)
    
    def _record_gesture_sequence(self, duration_s: float = 2.0, sample_rate_hz: float = 50.0, 
                                debug: bool = False) -> List[Tuple[float, float, float, float, float, float]]:
        """
        Record IMU sequence. Longer duration for complex gestures (1-8).
        """
        samples: List[Tuple[float, float, float, float, float, float]] = []
        dt = 1.0 / sample_rate_hz
        num_samples = int(duration_s * sample_rate_hz)
        
        for i in range(num_samples):
            sample = self.imu.read_sample()
            samples.append(sample)
            if debug:
                print(f"Sample {i}: ax={sample[0]:.2f}, ay={sample[1]:.2f}, az={sample[2]:.2f}, "
                      f"gx={sample[3]:.2f}, gy={sample[4]:.2f}, gz={sample[5]:.2f}")
            time.sleep(dt)
        
        return samples
    
    def send_vote(self, target_player: int):
        """Send vote to server."""
        try:
            client = client_connect(self.server_ip, self.server_port)
            send_json(client, self.player_id, "vote", target_player)
            client.close()
            print(f"[GyroGesture] Sent vote: player {self.player_id} -> target {target_player}")
        except (ConnectionRefusedError, OSError) as e:
            vote_message = {
                "player": self.player_id,
                "action": "vote",
                "target": target_player
            }
            print(f"[GyroGesture] Server not available (connection error: {e})")
            print(f"[GyroGesture] Would send: {vote_message}")
    
    def train_template(self, digit: int):
        """
        Record a template gesture for a specific digit.
        Useful for calibration/training.
        """
        print(f"\n=== Training Template for Digit {digit} ===")
        print(f"Draw the digit {digit} with the BerryIMU.")
        input("Press Enter when ready to record...")
        
        print("Recording template...")
        samples = self._record_gesture_sequence(duration_s=5.0, sample_rate_hz=50.0)
        self.recognizer.add_template(digit, samples)
        print(f"Template for digit {digit} recorded!")
    
    def run_interactive(self):
        """Interactive loop for gesture recognition and voting."""
        print("=== Gyroscope-Based Gesture Voting Client (Digits 1-8) ===")
        print(f"Player ID: {self.player_id}")
        print("Draw digits 1-8 with the BerryIMU to vote.")
        print("Commands:")
        print("  Enter: Record and recognize gesture")
        print("  't <digit>': Train template for digit (e.g., 't 1')")
        print("  'q': Quit")
        
        while True:
            cmd = input("\nCommand (Enter to record, 't <digit>' to train, 'q' to quit): ").strip().lower()
            
            if cmd == "q":
                print("Exiting gesture client.")
                break
            
            if cmd.startswith("t "):
                try:
                    digit = int(cmd.split()[1])
                    if 1 <= digit <= 8:
                        self.train_template(digit)
                    else:
                        print("Digit must be 1-8")
                except (ValueError, IndexError):
                    print("Usage: 't <digit>' where digit is 1-8")
                continue
            
            print("Recording gesture... draw a digit (1-8) now.")
            samples = self._record_gesture_sequence(duration_s=2.0, sample_rate_hz=50.0, debug=False)
            print("Recognizing...")
            
            digit = self.recognizer.classify(samples)
            if digit is None:
                print("Could not recognize gesture. Try again.")
                continue
            
            if digit not in range(1, 9):
                print(f"Recognized digit {digit}, but only 1-8 are valid. Ignoring.")
                continue
            
            print(f"Recognized gesture as digit {digit} (vote for player {digit}).")
            
            confirm = input(f"Send vote for player {digit}? (y/n): ").strip().lower()
            if confirm == "y":
                self.send_vote(digit)
            else:
                print("Vote cancelled.")


def test_imu_readings():
    """Test function to continuously read IMU values."""
    print("=== BerryIMU Test Mode ===")
    print("Press Ctrl+C to stop.\n")
    
    imu = BerryIMUInterface(debug=True)
    
    try:
        while True:
            sample = imu.read_sample()
            print(f"ax={sample[0]:8.2f}, ay={sample[1]:8.2f}, az={sample[2]:8.2f}, "
                  f"gx={sample[3]:8.2f}, gy={sample[4]:8.2f}, gz={sample[5]:8.2f}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[Test] Stopped.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_imu_readings()
        sys.exit(0)
    
    # Configuration
    SERVER_IP = "10.65.171.192"
    SERVER_PORT = 5050
    PLAYER_ID = 1
    DEBUG_IMU = True
    DEBUG_RECOGNITION = True  # Set to True to see detailed recognition debug info
    
    print("=== Gyroscope-Based Gesture Voting Client (Digits 1-8) ===")
    print("To test IMU readings only, run: python3 gyroGesture.py test")
    print()
    
    client = GestureVotingClient(SERVER_IP, SERVER_PORT, PLAYER_ID, debug_imu=DEBUG_IMU, debug_recognition=DEBUG_RECOGNITION)
    client.run_interactive()
