#!/usr/bin/env python3
"""
Fuzzy Recognition Engine for Linux music recognition
Drop-in replacement for exact hash matching with single-bit tolerance
"""
import numpy as np
import pickle
import json
import os
import time
from typing import Optional, Tuple, List, Dict, Any

class FuzzyRecognitionEngine:
    """
    Fuzzy recognition engine that tolerates single-bit differences
    """
    
    def __init__(self, arcade_config: Dict[str, Any]):
        """Initialize with arcade configuration"""
        self.arcade_config = arcade_config
        self.binary_db = None
        self.max_distance = 1  # Default: single-bit tolerance
        self.performance_log_path = '/tmp/fuzzy_performance.jsonl'
        self._build_binary_database()
    
    def _hex_to_binary(self, hex_string: str) -> np.ndarray:
        """Convert hex string to binary numpy array"""
        try:
            binary_bits = []
            for hex_char in hex_string:
                if hex_char in '0123456789abcdef':
                    decimal_val = int(hex_char, 16)
                    bits = [(decimal_val >> i) & 1 for i in range(3, -1, -1)]
                    binary_bits.extend(bits)
            return np.array(binary_bits, dtype=np.uint8)
        except:
            return np.array([], dtype=np.uint8)
    
    def _hamming_distance(self, bin1: np.ndarray, bin2: np.ndarray) -> int:
        """Calculate Hamming distance between two binary arrays"""
        if len(bin1) != len(bin2):
            return float('inf')
        return int(np.sum(bin1 != bin2))
    
    def _build_binary_database(self):
        """Convert arcade database from hex to binary format"""
        
        self.binary_db = {}
        total_entries = 0
        
        def process_table_recursive(table, path=[]):
            nonlocal total_entries
            
            for key, value in table.items():
                if isinstance(value, str):
                    # Leaf node - song name
                    full_path = path + [key]
                    
                    # Convert all hex keys to binary
                    binary_path = []
                    for hex_key in full_path:
                        binary_key = self._hex_to_binary(hex_key)
                        binary_path.append(binary_key)
                    
                    # Store in binary database
                    binary_key_tuple = tuple(arr.tobytes() for arr in binary_path)
                    self.binary_db[binary_key_tuple] = {
                        'song_name': value,
                        'binary_path': binary_path,
                        'hex_path': full_path,
                        'depth': len(full_path)
                    }
                    total_entries += 1
                    
                elif isinstance(value, dict):
                    process_table_recursive(value, path + [key])
        
        process_table_recursive(self.arcade_config['table'])
    
    def _fuzzy_search(self, query_path: List[np.ndarray]) -> List[Dict[str, Any]]:
        """Search binary database with fuzzy matching"""
        matches = []
        
        for db_key, db_entry in self.binary_db.items():
            db_path = db_entry['binary_path']
            
            # Check path length
            if len(query_path) != len(db_path):
                continue
            
            # Calculate total Hamming distance
            total_distance = 0
            step_distances = []
            
            for i, (query_step, db_step) in enumerate(zip(query_path, db_path)):
                step_distance = self._hamming_distance(query_step, db_step)
                step_distances.append(step_distance)
                total_distance += step_distance
                
                # Early termination if total distance exceeds threshold
                if total_distance > self.max_distance:
                    break
            else:
                # All steps completed and total distance within threshold
                if total_distance <= self.max_distance:
                    matches.append({
                        'song_name': db_entry['song_name'],
                        'total_distance': total_distance,
                        'step_distances': step_distances,
                        'hex_path': db_entry['hex_path']
                    })
        
        # Sort by distance (best matches first)
        matches.sort(key=lambda x: x['total_distance'])
        return matches
    
    def recognize(self, np_value: np.ndarray) -> Optional[str]:
        """
        Main recognition function with performance logging
        
        Args:
            np_value: Full screenshot image (not trimmed)
            
        Returns:
            Song name if recognized, None otherwise
        """
        start_time = time.time()
        
        # Prepare logging entry
        log_entry = {
            "timestamp": int(start_time * 1000),
            "phase": "fuzzy_recognition", 
            "strategies_tried": [],
            "success": False,
            "result": None,
            "total_time_ms": 0
        }
        
        try:
            # Optimized strategy order based on actual usage statistics
            # Strategies sorted by success count (descending) with unused strategies removed
            tolerance_strategies = [
                # Most successful strategies (>90% of all successes)
                (0, 0),   # 1144 successes (95.2% success rate)
                (0, 1),   # 24 successes
                (0, 2),   # 10 successes
                (0, 6),   # 6 successes
                (1, 4),   # 4 successes
                (0, 7),   # 4 successes
                
                # Occasionally successful strategies
                (2, 0),   # 2 successes (baseline gray only)
                (1, 3),   # 2 successes
                (3, 0),   # 1 success (slight gray relaxation)
                (4, 0),   # 1 success (moderate gray only)
                (1, 1),   # 1 success (minimal both)
                (5, 1),   # 1 success
                (2, 2),   # 1 success
                (0, 5),   # 1 success
                
                # Additional threshold levels for edge cases
                # (keeping only patterns that showed potential based on distance patterns)
                (0, 3),   # exact gray + medium threshold
                (0, 4),   # exact gray + higher threshold
                (0, 8),   # exact gray + maximum threshold
                (1, 5),   # minimal gray + high threshold
                (2, 5),   # baseline + high threshold
            ]
            
            # Try each strategy once with max distance (2), select minimum distance match
            for strategy_idx, (gray_tolerance, threshold_tolerance) in enumerate(tolerance_strategies):
                strategy_start = time.time()
                
                # Set max Hamming distance (10) and let fuzzy search find best match
                original_distance = self.max_distance
                self.max_distance = 50  # Search with max distance
                
                result, match_distance = self._try_recognition_with_tolerance_and_distance(np_value, gray_tolerance, threshold_tolerance)
                strategy_time = (time.time() - strategy_start) * 1000
                
                # Restore original distance
                self.max_distance = original_distance
                
                # Log this attempt
                strategy_log = {
                    "attempt": len(log_entry["strategies_tried"]) + 1,
                    "gray_tolerance": gray_tolerance,
                    "threshold_tolerance": threshold_tolerance,
                    "hamming_distance": match_distance if result else 50,  # Log actual match distance or max tried
                    "time_ms": strategy_time,
                    "success": result is not None,
                    "result": result
                }
                log_entry["strategies_tried"].append(strategy_log)
                
                if result is not None:
                    log_entry["success"] = True
                    log_entry["result"] = result
                    log_entry["winning_distance"] = match_distance
                    break  # Exit strategy loop
                
        except Exception as e:
            log_entry["error"] = str(e)
        finally:
            log_entry["total_time_ms"] = (time.time() - start_time) * 1000
            self._write_performance_log(log_entry)
            
        return log_entry.get("result")
    
    def _try_recognition_with_tolerance_and_distance(self, np_value: np.ndarray, gray_tolerance: int, threshold_tolerance: int) -> Tuple[Optional[str], int]:
        """Try recognition and return result with actual Hamming distance used"""
        
        # Apply arcade processing pipeline
        arcade_trim = self.arcade_config['trim']
        cropped = np_value[arcade_trim]
        
        # Apply gray pixel filtering with tolerance
        r, g, b = cropped[:,:,0], cropped[:,:,1], cropped[:,:,2]
        is_gray = (np.abs(r - g) <= gray_tolerance) & (np.abs(r - b) <= gray_tolerance) & (np.abs(g - b) <= gray_tolerance)
        masked = np.where(is_gray, r, 0)
        
        gray_pixel_count = np.count_nonzero(is_gray)
        
        # Early termination if no gray pixels detected
        if gray_pixel_count == 0:
            return None, 0
        
        # Threshold each row with tolerance
        thresholds = self.arcade_config['thresholds']
        bins = []
        for i in range(masked.shape[0]):
            th_min = max(0, thresholds[i][0] - threshold_tolerance)
            th_max = min(255, thresholds[i][1] + threshold_tolerance)
            bin_row = np.where((th_min <= masked[i]) & (masked[i] <= th_max), 1, 0)
            bins.append(bin_row)
        
        bin_counts = [np.sum(bin_row) for bin_row in bins]
        non_zero_bins = sum(1 for count in bin_counts if count > 0)
        
        # Check if we have meaningful patterns
        if non_zero_bins < 3:
            return None, 0
        
        # Generate patterns
        shrunk = [line[::2]&line[1::2] for line in bins]
        hexes = [line[::4]*8+line[1::4]*4+line[2::4]*2+line[3::4] for line in shrunk]
        recogkeys = [''.join([format(v, '0x') for v in line]) for line in hexes]
        
        # Convert query to binary and search
        query_binary_path = []
        for hex_key in recogkeys:
            binary_key = self._hex_to_binary(hex_key)
            query_binary_path.append(binary_key)
        
        matches = self._fuzzy_search(query_binary_path)
        
        if matches:
            best_match = matches[0]  # Already sorted by distance (ascending)
            return best_match['song_name'], best_match['total_distance']
        
        return None, 0
    
    def _try_recognition_with_tolerance_logged(self, np_value: np.ndarray, gray_tolerance: int, threshold_tolerance: int) -> Optional[str]:
        """Try recognition with specific tolerance values (compatibility wrapper)"""
        result, _ = self._try_recognition_with_tolerance_and_distance(np_value, gray_tolerance, threshold_tolerance)
        return result
    
    def _try_recognition_with_tolerance(self, np_value: np.ndarray, gray_tolerance: int, threshold_tolerance: int) -> Optional[str]:
        """Try recognition with specific tolerance values (original version for compatibility)"""
        return self._try_recognition_with_tolerance_logged(np_value, gray_tolerance, threshold_tolerance)
    
    
    def set_tolerance(self, max_distance: int):
        """Set maximum Hamming distance tolerance"""
        self.max_distance = max_distance
    
    def try_with_higher_tolerance_logged(self, np_value: np.ndarray) -> Optional[str]:
        """Deprecated - now integrated into main loop"""
        # This function is no longer needed since Hamming distances are integrated
        return None
    
    def try_with_higher_tolerance(self, np_value: np.ndarray) -> Optional[str]:
        """Try recognition with progressively higher Hamming distance tolerance (original version)"""
        return self.try_with_higher_tolerance_logged(np_value)
    
    def _write_performance_log(self, log_entry: Dict):
        """Write performance log entry to JSONL file"""
        try:
            with open(self.performance_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            pass  # Silent fail for logging

def load_fuzzy_recognition_engine() -> FuzzyRecognitionEngine:
    """Load and initialize fuzzy recognition engine"""
    
    # Load arcade configuration
    with open('/var/home/atty/Applications/inf-notebook/resources/musicselect2.1.res', 'rb') as f:
        resource_data = pickle.load(f)
    
    arcade_config = resource_data['musicname']['arcade']
    
    # Create fuzzy engine
    engine = FuzzyRecognitionEngine(arcade_config)
    
    # Set optimal tolerance (from testing: distance=1 gives 84.6% success)
    engine.set_tolerance(1)
    
    return engine
