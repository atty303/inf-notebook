#!/usr/bin/env python3
"""
Main Loop Logger
Unified logging system for main loop events with code versioning
"""
import os
import time
import json
from typing import Dict, Any, Optional

class MainLoopLogger:
    """Centralized logger for main loop events with versioning"""
    
    # Code version - increment this when making significant changes
    CODE_VERSION = "2.1.0"
    
    def __init__(self, session_id: Optional[int] = None):
        """Initialize logger with session-specific log file"""
        self.session_id = session_id or int(time.time() * 1000)
        
        # Setup cache directory
        cache_dir = os.path.expanduser('~/.cache/inf-notebook')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Create log file path
        self.log_file_path = os.path.join(
            cache_dir, 
            f'main_loop_v{self.CODE_VERSION}_{self.session_id}.jsonl'
        )
        
        # Log initialization
        self._write_log({
            "event": "logger_initialized",
            "code_version": self.CODE_VERSION,
            "session_id": self.session_id,
            "log_file": self.log_file_path
        })
    
    def _write_log(self, entry: Dict[str, Any]) -> None:
        """Write log entry to file with timestamp and version"""
        try:
            # Add standard fields
            log_entry = {
                "timestamp": int(time.time() * 1000),
                "code_version": self.CODE_VERSION,
                "session_id": self.session_id,
                **entry
            }
            
            with open(self.log_file_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception:
            # Silent fail for logging to avoid breaking main application
            pass
    
    def log_main_loop_cycle(self, sleep_time: float, loop_time_ms: float, 
                          handle: int, active: bool, waiting: bool, 
                          musicselect: bool, screen_latest: Optional[str],
                          xy: Optional[tuple]) -> None:
        """Log main loop cycle information"""
        self._write_log({
            "event": "main_loop_cycle",
            "sleep_time": sleep_time,
            "loop_time_ms": loop_time_ms,
            "handle": handle,
            "active": active,
            "waiting": waiting,
            "musicselect": musicselect,
            "screen_latest": screen_latest,
            "xy": list(xy) if xy else None
        })
    
    def log_screen_detection(self, screen_result: Optional[str], 
                           screen_previous: Optional[str],
                           detection_time_ms: float,
                           rect: Optional[tuple], xy: Optional[tuple]) -> None:
        """Log screen detection results"""
        self._write_log({
            "event": "screen_detection",
            "screen_result": screen_result,
            "screen_previous": screen_previous,
            "screen_changed": screen_result != screen_previous,
            "detection_time_ms": detection_time_ms,
            "rect": list(rect) if rect else None,
            "xy": list(xy) if xy else None
        })
    
    def log_screen_transition(self, from_screen: Optional[str], 
                            to_screen: Optional[str],
                            active: bool, waiting: bool, musicselect: bool) -> None:
        """Log screen transitions"""
        self._write_log({
            "event": "screen_transition",
            "from_screen": from_screen,
            "to_screen": to_screen,
            "active": active,
            "waiting": waiting,
            "musicselect": musicselect
        })
    
    def log_sleep_time_change(self, reason: str, old_sleep_time: float,
                            new_sleep_time: float, screen: Optional[str],
                            waiting: bool, musicselect: bool, 
                            processed: bool = False) -> None:
        """Log sleep time changes"""
        self._write_log({
            "event": "sleep_time_change",
            "reason": reason,
            "old_sleep_time": old_sleep_time,
            "new_sleep_time": new_sleep_time,
            "screen": screen,
            "waiting": waiting,
            "musicselect": musicselect,
            "processed": processed
        })
    
    def log_screenshot_taken(self, screen: Optional[str], shot_success: bool,
                           image_shape: Optional[tuple]) -> None:
        """Log screenshot attempts"""
        self._write_log({
            "event": "screenshot_taken",
            "screen": screen,
            "shot_success": shot_success,
            "image_shape": list(image_shape) if image_shape else None
        })
    
    def log_version_detection(self, success: bool, version: Optional[str],
                            screen: Optional[str], active: bool, 
                            musicselect: bool) -> None:
        """Log version detection results"""
        self._write_log({
            "event": "version_detection",
            "success": success,
            "version": version,
            "screen": screen,
            "active": active,
            "musicselect": musicselect
        })
    
    def log_musicselect_queue_submit(self, version: Optional[str], 
                                   queue_size: int) -> None:
        """Log successful musicselect queue submissions"""
        self._write_log({
            "event": "musicselect_queue_submit",
            "version": version,
            "queue_size": queue_size
        })
    
    def log_musicselect_queue_full(self, version: Optional[str]) -> None:
        """Log musicselect queue full events"""
        self._write_log({
            "event": "musicselect_queue_full",
            "version": version
        })
    
    def log_custom_event(self, event_name: str, **kwargs) -> None:
        """Log custom events with arbitrary data"""
        self._write_log({
            "event": event_name,
            **kwargs
        })
    
    def get_log_file_path(self) -> str:
        """Get the current log file path"""
        return self.log_file_path
    
    def get_code_version(self) -> str:
        """Get the current code version"""
        return self.CODE_VERSION