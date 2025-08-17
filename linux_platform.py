import subprocess
import os
from pathlib import Path
from typing import Optional
from logging import getLogger

from platform_service import PlatformService, GameDetector

logger = getLogger(__name__)

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
        """Linux doesn't support game detection - OBS only"""
        logger.info('Game detection not available on Linux - using OBS capture only')
        return None