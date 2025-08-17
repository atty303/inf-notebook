from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Iterator
from dataclasses import dataclass

@dataclass
class Rectangle:
    left: int
    top: int
    right: int
    bottom: int
    
    @property
    def width(self) -> int:
        return self.right - self.left
    
    @property
    def height(self) -> int:
        return self.bottom - self.top

WindowHandle = int

class GameDetector(ABC):
    """Interface for game window detection and monitoring"""
    
    @abstractmethod
    def find_game_window(self, title: str, executable: str) -> Optional[WindowHandle]:
        """Find game window by title and executable name"""
        pass
    
    @abstractmethod
    def get_window_position(self, handle: WindowHandle) -> Optional[Rectangle]:
        """Get window position and size"""
        pass
    
    @abstractmethod
    def validate_game_resolution(self, rect: Rectangle) -> bool:
        """Check if window size is valid for the game"""
        pass

class PlatformService(ABC):
    """Abstract interface for platform-specific operations"""
    
    @abstractmethod
    def prevent_multiple_instances(self, app_title: str) -> bool:
        """Check if application is already running. Returns True if already running."""
        pass
    
    @abstractmethod
    def get_app_window_handle(self, app_title: str) -> Optional[WindowHandle]:
        """Get application window handle. Returns None if not found."""
        pass
    
    @abstractmethod
    def show_error_dialog(self, message: str, title: str):
        """Display error message dialog to user"""
        pass
    
    @abstractmethod
    def configure_app_window(self, handle: WindowHandle):
        """Configure application window settings (disable maximize, etc.)"""
        pass
    
    @abstractmethod
    def open_folder_in_explorer(self, path: str) -> bool:
        """Open folder in system file manager. Returns True on success."""
        pass
    
    @abstractmethod
    def get_config_directory(self) -> Path:
        """Get platform-appropriate configuration directory"""
        pass
    
    @abstractmethod
    def get_cache_directory(self) -> Path:
        """Get platform-appropriate cache directory"""
        pass
    
    @abstractmethod
    def absolute_path(self, path_str: str) -> Path:
        """Create platform-appropriate absolute Path object from string"""
        pass
    
    @abstractmethod
    def create_game_detector(self) -> Optional[GameDetector]:
        """Create game detector for window management. Returns None if not supported (OBS-only)."""
        pass