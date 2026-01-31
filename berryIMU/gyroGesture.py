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
    Tracks the 2D rotation pattern from gyroscope data for flat-surface tracing.
    Uses raw gyroscope values directly - no integration needed.
    For flat table tracing, Z-axis (yaw) is primary, X/Y are secondary.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset trajectory state."""
        self.trajectory = []
    
    def process_samples(self, samples: List[Tuple[float, float, float, float, float, float]], 
                       dt: float = 0.02) -> List[Tuple[float, float, float]]:
        """
        Process IMU samples to extract rotation pattern from raw gyroscope values.
        For flat table tracing, we use raw gyro values directly.
        
        Args:
            samples: List of (ax, ay, az, gx, gy, gz) tuples
            dt: Time step between samples (default 0.02s for 50Hz) - not used for raw values
        
        Returns:
            List of (gx, gy, gz) raw gyroscope values (rotation rates)
        """
        self.reset()
        gyro_pattern = []
        
        # Remove baseline (drift/bias) using first few samples (assuming device is at rest initially)
        if len(samples) >= 3:
            baseline_gx = sum(s[3] for s in samples[:3]) / 3
            baseline_gy = sum(s[4] for s in samples[:3]) / 3
            baseline_gz = sum(s[5] for s in samples[:3]) / 3
        else:
            baseline_gx = baseline_gy = baseline_gz = 0.0
        
        for sample in samples:
            ax, ay, az, gx, gy, gz = sample
            
            # Remove baseline (gyroscope bias/drift) but keep raw rotation rates
            # These represent the rotation pattern directly
            gx_clean = gx - baseline_gx
            gy_clean = gy - baseline_gy
            gz_clean = gz - baseline_gz
            
            # Use raw gyroscope values directly - they represent the rotation pattern
            # gz is primary for flat table (yaw rotation)
            # gx, gy are secondary (roll/pitch if device tilts slightly)
            gyro_pattern.append((gx_clean, gy_clean, gz_clean))
        
        return gyro_pattern


class GestureFeatureExtractor:
    """
    Extracts features from raw gyroscope rotation patterns for flat-surface tracing.
    Focuses on Z-axis (yaw) rotation patterns which are primary for 2D table tracing.
    """
    
    @staticmethod
    def extract_features(gyro_pattern: List[Tuple[float, float, float]], 
                        samples: List[Tuple[float, float, float, float, float, float]]) -> Dict[str, float]:
        """
        Extract features from raw gyroscope rotation patterns for flat-surface tracing.
        
        For flat table tracing:
        - Z-axis (gz) is primary - rotation around vertical axis (yaw) as you move left/right
        - X/Y axes are secondary - minimal rotation when device stays flat
        
        Returns a dictionary of features useful for digit classification.
        """
        if len(gyro_pattern) < 3:
            return {}
        
        features = {}
        
        # Convert to numpy arrays for easier computation
        gyro_array = np.array(gyro_pattern)  # Shape: (n_samples, 3) - (gx, gy, gz)
        gx_values = gyro_array[:, 0]
        gy_values = gyro_array[:, 1]
        gz_values = gyro_array[:, 2]  # Primary axis for flat table tracing
        
        # 1. Z-axis rotation direction changes (zero crossings) - primary for 2D tracing
        # This detects when rotation direction changes (left vs right)
        z_zero_crossings = 0
        if len(gz_values) > 1:
            for i in range(1, len(gz_values)):
                if (gz_values[i-1] > 0 and gz_values[i] < 0) or (gz_values[i-1] < 0 and gz_values[i] > 0):
                    z_zero_crossings += 1
        features['z_zero_crossings'] = z_zero_crossings
        
        # 2. Total Z-axis rotation magnitude (sum of absolute values)
        # Measures total rotation activity in the primary axis
        total_z_rotation = np.sum(np.abs(gz_values))
        features['total_z_rotation'] = total_z_rotation
        
        # 3. Z-axis rotation range (max - min)
        z_range = np.max(gz_values) - np.min(gz_values)
        features['z_rotation_range'] = z_range
        
        # 4. Number of peaks in Z-axis rotation (indicates strokes/direction changes)
        if len(gz_values) > 3:
            threshold = np.mean(np.abs(gz_values)) + 0.5 * np.std(np.abs(gz_values))
            peaks = sum(1 for i in range(1, len(gz_values) - 1) 
                       if abs(gz_values[i]) > threshold and 
                       abs(gz_values[i]) > abs(gz_values[i-1]) and 
                       abs(gz_values[i]) > abs(gz_values[i+1]))
            features['z_rotation_peaks'] = peaks
        else:
            features['z_rotation_peaks'] = 0
        
        # 5. Z-axis rotation smoothness (standard deviation of rotation rate)
        # Lower = smoother, higher = more jerky
        features['z_rotation_smoothness'] = np.std(gz_values)
        
        # 6. Dominant rotation direction (positive vs negative Z rotation)
        # Positive = clockwise, Negative = counter-clockwise
        positive_z = np.sum(gz_values[gz_values > 0])
        negative_z = abs(np.sum(gz_values[gz_values < 0]))
        if positive_z + negative_z > 0:
            features['z_rotation_direction'] = positive_z / (positive_z + negative_z)  # 0-1, higher = more clockwise
        else:
            features['z_rotation_direction'] = 0.5
        
        # 7. X/Y rotation magnitude (should be minimal for flat table)
        # If high, device might be tilting
        xy_magnitude = np.mean(np.linalg.norm(gyro_array[:, :2], axis=1))
        features['xy_rotation'] = xy_magnitude
        
        # 8. Loop detection using Z-axis pattern
        # For digits like 6, 8 - check if Z rotation pattern repeats
        if len(gz_values) > 20:
            # Check if second half of pattern is similar to first half
            mid = len(gz_values) // 2
            first_half = gz_values[:mid]
            second_half = gz_values[mid:]
            # Simple correlation: if patterns are similar, it's a loop
            if len(first_half) == len(second_half):
                correlation = np.corrcoef(first_half, second_half)[0, 1]
                features['loop_score'] = max(0, correlation) if not np.isnan(correlation) else 0.0
            else:
                features['loop_score'] = 0.0
        else:
            features['loop_score'] = 0.0
        
        # 9. Total path complexity (sum of all rotation magnitudes)
        total_rotation = np.sum(np.linalg.norm(gyro_array, axis=1))
        features['total_rotation'] = total_rotation
        
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
        
        # Feature-based classification rules for flat-surface tracing
        # Based on Z-axis rotation patterns (primary) and X/Y rotation (secondary)
        # These will need tuning with actual data
        self.digit_features = {
            # Digit 1: Simple vertical line - mostly one direction, few zero crossings
            1: {'z_zero_crossings': (0, 2), 'z_rotation_peaks': (0, 3), 'total_z_rotation': (50, 500)},
            # Digit 2: Curved shape - some direction changes
            2: {'z_zero_crossings': (1, 4), 'z_rotation_peaks': (2, 6)},
            # Digit 3: Two curves - more direction changes
            3: {'z_zero_crossings': (2, 6), 'z_rotation_peaks': (3, 8)},
            # Digit 4: Multiple strokes with corners - many direction changes
            4: {'z_zero_crossings': (3, 8), 'z_rotation_peaks': (4, 10)},
            # Digit 5: Complex shape - many changes
            5: {'z_zero_crossings': (4, 10), 'z_rotation_peaks': (5, 12)},
            # Digit 6: Loop at bottom - circular pattern
            6: {'z_zero_crossings': (2, 6), 'loop_score': (0.2, 1.0), 'z_rotation_peaks': (3, 8)},
            # Digit 7: Diagonal line with hook - moderate changes
            7: {'z_zero_crossings': (1, 5), 'z_rotation_peaks': (2, 7)},
            # Digit 8: Two loops - strong circular pattern
            8: {'z_zero_crossings': (4, 12), 'loop_score': (0.3, 1.0), 'z_rotation_peaks': (6, 15)}
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
        gyro_pattern = self.tracker.process_samples(samples, dt)
        if len(gyro_pattern) > 0:
            gyro_array = np.array(gyro_pattern)
            normalized = self.dtw_matcher.normalize_sequence(gyro_array)
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
        
        # Check minimum movement threshold using Z-axis gyroscope (primary for flat table)
        gz_values = [s[5] for s in samples]
        max_gz = max(gz_values)
        min_gz = min(gz_values)
        if abs(max_gz - min_gz) < 30:  # Too little Z-axis rotation
            return None
        
        # Extract raw gyroscope rotation pattern
        dt = 0.02  # 50Hz
        gyro_pattern = self.tracker.process_samples(samples, dt)
        
        if len(gyro_pattern) < 5:
            return None
        
        # Extract features from raw gyro pattern
        features = self.feature_extractor.extract_features(gyro_pattern, samples)
        
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
            gyro_array = np.array(gyro_pattern)
            normalized_input = self.dtw_matcher.normalize_sequence(gyro_array)
            
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
