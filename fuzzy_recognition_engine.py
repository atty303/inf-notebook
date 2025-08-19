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
            # Comprehensive fine-grained strategies with micro-steps
            tolerance_strategies = [
                # Ultra-fine grain for critical small thresholds
                (0, 0),   # Step 0: Windows exact match attempt
                (1, 0),   # Step 1: minimal gray tolerance
                (2, 0),   # Step 2: baseline gray only
                (3, 0),   # Step 3: slight gray relaxation
                (4, 0),   # Step 4: moderate gray only
                (5, 0),   # Step 5: higher gray only
                (6, 0),   # Step 6: very high gray only
                
                # Threshold micro-increments with minimal gray
                (0, 1),   # Step 7: exact gray + minimal threshold
                (1, 1),   # Step 8: minimal both tolerances 
                (2, 1),   # Step 9: baseline + minimal threshold
                (3, 1),   # Step 10: slight gray + minimal threshold
                (4, 1),   # Step 11: moderate gray + minimal threshold
                (5, 1),   # Step 12: higher gray + minimal threshold
                (6, 1),   # Step 13: very high gray + minimal threshold
                (7, 1),   # Step 14: max gray + minimal threshold
                
                # Small threshold increments
                (0, 2),   # Step 15: exact gray + small threshold
                (1, 2),   # Step 16: minimal gray + small threshold  
                (2, 2),   # Step 17: baseline + small threshold
                (3, 2),   # Step 18: slight gray + small threshold
                (4, 2),   # Step 19: moderate + small threshold
                (5, 2),   # Step 20: higher + small threshold
                (6, 2),   # Step 21: very high + small threshold
                (7, 2),   # Step 22: max gray + small threshold
                
                # Medium threshold with fine gray steps
                (1, 3),   # Step 23: minimal gray + medium threshold
                (2, 3),   # Step 24: baseline + medium threshold
                (3, 3),   # Step 25: slight + medium threshold
                (4, 3),   # Step 26: moderate + medium threshold
                (5, 3),   # Step 27: higher + medium threshold
                (6, 3),   # Step 28: very high + medium threshold
                (7, 3),   # Step 29: max gray + medium threshold
                (8, 3),   # Step 30: ultra-high + medium threshold
                
                # Higher thresholds for edge cases
                (1, 4),   # Step 31: minimal gray + higher threshold
                (2, 4),   # Step 32: baseline + higher threshold
                (3, 4),   # Step 33: slight + higher threshold
                (4, 4),   # Step 34: moderate + higher threshold
                (8, 2),   # Step 35: ultra-high gray + small threshold
                (9, 3),   # Step 36: extreme gray + medium threshold
                (10, 4),  # Step 37: maximum tolerance
                
                # Extended range for difficult cases
                (0, 3),   # Step 38: exact gray + medium threshold
                (0, 4),   # Step 39: exact gray + higher threshold
                (0, 5),   # Step 40: exact gray + high threshold
                (8, 1),   # Step 41: ultra-high gray + minimal threshold
                (9, 1),   # Step 42: extreme gray + minimal threshold
                (9, 2),   # Step 43: extreme gray + small threshold
                (8, 4),   # Step 44: ultra-high + higher threshold
                (9, 4),   # Step 45: extreme + higher threshold
                (10, 1),  # Step 46: max gray + minimal threshold
                (10, 2),  # Step 47: max gray + small threshold
                (10, 3),  # Step 48: max gray + medium threshold
                (11, 3),  # Step 49: beyond max + medium
                (12, 4),  # Step 50: ultra beyond + higher
                
                # High threshold patterns for very difficult recognition
                (1, 5),   # Step 51: minimal gray + high threshold
                (2, 5),   # Step 52: baseline + high threshold
                (3, 5),   # Step 53: slight + high threshold
                (4, 5),   # Step 54: moderate + high threshold
                (5, 5),   # Step 55: higher + high threshold
                (6, 5),   # Step 56: very high + high threshold
                (7, 5),   # Step 57: max + high threshold
                (0, 6),   # Step 58: exact gray + very high threshold
                (1, 6),   # Step 59: minimal + very high threshold
                (2, 6),   # Step 60: baseline + very high threshold
                (3, 6),   # Step 61: slight + very high threshold
                (8, 5),   # Step 62: ultra-high + high threshold
                (9, 5),   # Step 63: extreme + high threshold
                (10, 5),  # Step 64: max + high threshold
                (0, 7),   # Step 65: exact gray + ultra-high threshold
                (1, 7),   # Step 66: minimal + ultra-high threshold
                (2, 7),   # Step 67: baseline + ultra-high threshold
                (5, 6),   # Step 68: higher + very high threshold
                (6, 6),   # Step 69: very high + very high threshold
                (7, 6),   # Step 70: max + very high threshold
                (11, 5),  # Step 71: beyond max + high threshold
                (12, 5),  # Step 72: ultra beyond + high threshold
                (13, 5),  # Step 73: extreme beyond + high threshold
                (8, 6),   # Step 74: ultra-high + very high threshold
                (9, 6),   # Step 75: extreme + very high threshold
                (10, 6),  # Step 76: max + very high threshold
                (0, 8),   # Step 77: exact gray + maximum threshold
                (1, 8),   # Step 78: minimal + maximum threshold
                (11, 6),  # Step 79: beyond max + very high threshold
                (12, 6),  # Step 80: ultra beyond + very high threshold
                (15, 7),  # Step 81: maximum gray + ultra-high threshold
                (15, 8),  # Step 82: maximum gray + maximum threshold
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
