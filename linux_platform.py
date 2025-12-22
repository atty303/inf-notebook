import subprocess
import os
from pathlib import Path
from typing import Optional
from logging import getLogger

from platform_service import PlatformService, GameDetector, WindowHandle, Rectangle

logger = getLogger(__name__)

class LinuxGameDetector(GameDetector):
    """Dummy game detector for Linux - always returns dummy values for OBS-only mode"""

    def find_game_window(self, title: str, executable: str) -> Optional[WindowHandle]:
        """Return dummy window handle since Linux uses OBS capture only"""
        return 1  # Dummy handle

    def get_window_position(self, handle: WindowHandle) -> Optional[Rectangle]:
        """Return dummy rectangle since Linux uses OBS capture only"""
        return Rectangle(0, 0, 1920, 1080)  # Dummy rectangle

    def validate_game_resolution(self, rect: Rectangle) -> bool:
        """Always return True since Linux uses OBS capture only"""
        return True

    def get_window_rect(self, handle: WindowHandle) -> Optional[Rectangle]:
        """Return dummy rectangle since Linux uses OBS capture only"""
        return Rectangle(0, 0, 1920, 1080)  # Dummy rectangle

    def is_window_active(self, handle: WindowHandle) -> bool:
        """Always return True since Linux uses OBS capture only"""
        return True

    def get_active_window_title(self) -> Optional[str]:
        """Return game window title to match Windows behavior"""
        return "beatmania IIDX INFINITAS"

class LinuxPlatformService(PlatformService):
    """Linux-specific platform service implementation (OBS-only)"""

    def prevent_multiple_instances(self, app_title: str) -> bool:
        """Check if application is already running using pidfile"""
        pidfile = Path.home() / '.local' / 'run' / 'inf-notebook.pid'

        if pidfile.exists():
            try:
                with open(pidfile, 'r') as f:
                    pid = int(f.read().strip())

                # Check if process is still running
                try:
                    subprocess.run(['kill', '-0', str(pid)], check=True, capture_output=True)
                    return True  # Process exists
                except subprocess.CalledProcessError:
                    # Process doesn't exist, remove stale pidfile
                    pidfile.unlink()
                    return False
            except (ValueError, FileNotFoundError):
                # Invalid pidfile, remove it
                pidfile.unlink()
                return False

        # Create pidfile for this instance
        pidfile.parent.mkdir(parents=True, exist_ok=True)
        with open(pidfile, 'w') as f:
            import os
            f.write(str(os.getpid()))

        return False

    def get_app_window_handle(self, app_title: str) -> Optional[int]:
        """Linux doesn't need window handle management"""
        return 1  # Dummy handle

    def show_error_dialog(self, message: str, title: str):
        """Display error dialog using zenity or fallback to console"""
        try:
            subprocess.run([
                'zenity', '--error',
                '--text', message,
                '--title', title
            ], check=False)
        except FileNotFoundError:
            # Fallback if zenity not available
            logger.error(f'{title}: {message}')
            print(f'ERROR - {title}: {message}')

    def configure_app_window(self, handle):
        """Linux window configuration (no-op, handled by window manager)"""
        # On Linux, window management is typically handled by the window manager
        # Most applications don't need to customize window behavior
        pass

    def open_folder_in_explorer(self, path: str) -> bool:
        """Open folder using xdg-open"""
        try:
            subprocess.run(['xdg-open', path], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as ex:
            logger.error(f'Failed to open folder: {ex}')
            return False

    def get_config_directory(self) -> Path:
        """Get XDG config directory (~/.config/inf-notebook)"""
        config_home = Path.home() / '.config'
        if 'XDG_CONFIG_HOME' in os.environ:
            config_home = Path(os.environ['XDG_CONFIG_HOME'])

        config_dir = config_home / 'inf-notebook'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def get_cache_directory(self) -> Path:
        """Get XDG cache directory (~/.local/share/inf-notebook)"""
        data_home = Path.home() / '.local' / 'share'
        if 'XDG_DATA_HOME' in os.environ:
            data_home = Path(os.environ['XDG_DATA_HOME'])

        cache_dir = data_home / 'inf-notebook'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def absolute_path(self, path_str: str) -> Path:
        """Create POSIX absolute Path object"""
        return Path(path_str).absolute()

    def create_game_detector(self) -> Optional[GameDetector]:
        """Create dummy game detector for Linux - OBS only but maintains Windows compatibility"""
        logger.info('Using dummy game detection on Linux - OBS capture only')
        return LinuxGameDetector()

    def register_hotkeys(self, bindings: dict) -> bool:
        """Register Linux global hotkeys - may fail due to permissions"""
        try:
            logger.info('Hotkeys not implemented on Linux')
            return True
        except PermissionError:
            logger.info('Hotkeys disabled on Linux due to permission requirements')
            return False
        except Exception as ex:
            logger.warning(f'Failed to register hotkeys on Linux: {ex}')
            return False

    def clear_hotkeys(self):
        """Clear Linux global hotkeys - no-op"""
        logger.info('Clearing hotkeys not implemented on Linux')
