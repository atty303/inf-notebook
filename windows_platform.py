import platform
from pathlib import WindowsPath
from os import system, environ
from os.path import exists
from typing import Optional
from logging import getLogger

from platform_service import PlatformService, GameDetector, Rectangle, WindowHandle

if platform.system() == 'Windows':
    from ctypes import (
        windll, c_bool, c_int, c_ulong, pointer, POINTER, WINFUNCTYPE, create_unicode_buffer
    )
    from ctypes.wintypes import RECT, DWORD, MAX_PATH
    from infnotebook import productname

logger = getLogger(__name__)

class WindowsGameDetector(GameDetector):
    """Windows-specific game window detection using Win32 API"""
    
    # Valid INFINITAS resolutions
    VALID_RESOLUTIONS = {
        (1920, 1080),
        (1536, 864), 
        (1280, 720),
        (1097, 617)
    }
    
    def __init__(self):
        # Set DPI awareness
        class PROCESS_DPI_AWARENESS:
            PROCESS_DPI_UNAWARE = 0
            PROCESS_SYSTEM_DPI_AWARE = 1
            PROCESS_PER_MONITOR_DPI_AWARE = 2
        
        windll.shcore.SetProcessDpiAwareness(PROCESS_DPI_AWARENESS.PROCESS_DPI_UNAWARE)
    
    def _get_process_filename(self, hWnd) -> str:
        """Get executable filename for window handle"""
        pId = c_ulong()
        windll.user32.GetWindowThreadProcessId(hWnd, pointer(pId))
        if not pId:
            return ""

        pHnd = windll.kernel32.OpenProcess(0x0410, 0, pId)
        if not pHnd:
            return ""

        filepath = create_unicode_buffer(MAX_PATH)
        length = DWORD(MAX_PATH)
        windll.kernel32.QueryFullProcessImageNameW(pHnd, 0, pointer(filepath), pointer(length))
        
        from os.path import basename
        return basename(filepath.value)
    
    def find_game_window(self, title: str, executable: str) -> Optional[WindowHandle]:
        """Find game window by title and executable name"""
        enumWindowsProc = WINFUNCTYPE(c_bool, c_int, POINTER(c_int))
        handles = []
        
        def foreach_window(hWnd, lParam):
            if windll.user32.IsHungAppWindow(hWnd):
                return True
                
            # Check window title
            length = windll.user32.GetWindowTextLengthW(hWnd)
            if not length:
                return True
                
            buff = create_unicode_buffer(length + 1)
            windll.user32.GetWindowTextW(hWnd, buff, length + 1)
            if buff.value != title:
                return True
            
            # Check executable name
            filename = self._get_process_filename(hWnd)
            if filename in [executable, ""]:
                handles.append(hWnd)
            return True
        
        windll.user32.EnumWindows(enumWindowsProc(foreach_window), 0)
        return handles[0] if len(handles) == 1 else None
    
    def get_window_position(self, handle: WindowHandle) -> Optional[Rectangle]:
        """Get window position and size"""
        if handle == 0:
            return None
        
        rect = RECT()
        windll.user32.GetWindowRect(handle, pointer(rect))
        return Rectangle(rect.left, rect.top, rect.right, rect.bottom)
    
    def validate_game_resolution(self, rect: Rectangle) -> bool:
        """Check if window size matches valid INFINITAS resolutions"""
        return (rect.width, rect.height) in self.VALID_RESOLUTIONS

class WindowsPlatformService(PlatformService):
    """Windows-specific platform service implementation"""
    
    def prevent_multiple_instances(self, app_title: str) -> bool:
        """Check if application window already exists"""
        handle = windll.user32.FindWindowW(None, app_title)
        return handle != 0
    
    def get_app_window_handle(self, app_title: str) -> Optional[int]:
        """Get application window handle"""
        handle = windll.user32.FindWindowW(None, app_title)
        return handle if handle != 0 else None
    
    def show_error_dialog(self, message: str, title: str):
        """Display Windows message box"""
        MB_OK = 0x0000
        windll.user32.MessageBoxW(0, message, title, MB_OK)
    
    def configure_app_window(self, handle: WindowHandle):
        """Configure Windows application window settings"""
        if handle == 0:
            return
            
        # Window style constants
        WS_MAXIMIZEBOX = 0x10000
        WS_THICKFRAME = 0x40000
        GWL_STYLE = -16
        SC_MAXMIZE = 0xf030
        MF_BYCOMMAND = 0x00
        SWP_NOSIZE = 0x01
        SWP_NOMOVE = 0x02
        SWP_NOZORDER = 0x04
        SWP_FRAMECHANGED = 0x20

        # Disable maximize and thick frame
        style = windll.user32.GetWindowLongW(handle, GWL_STYLE)
        style &= ~WS_MAXIMIZEBOX
        style &= ~WS_THICKFRAME
        windll.user32.SetWindowLongW(handle, GWL_STYLE, style)

        # Remove maximize from system menu
        hmenu = windll.user32.GetSystemMenu(handle, False)
        windll.user32.RemoveMenu(hmenu, SC_MAXMIZE, MF_BYCOMMAND)
        windll.user32.DrawMenuBar(handle)

        # Apply changes
        windll.user32.SetWindowPos(handle, None, 0, 0, 0, 0, 
                                  SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED)
    
    def open_folder_in_explorer(self, path: str) -> bool:
        """Open folder in Windows Explorer"""
        try:
            system(f'explorer.exe "{path}"')
            return True
        except Exception as ex:
            logger.error(f'Failed to open folder: {ex}')
            return False
    
    def get_config_directory(self) -> WindowsPath:
        """Get Windows AppData roaming directory"""
        path_str = environ.get('AppData')
        if not path_str or not exists(path_str):
            raise RuntimeError('AppData directory not found')
        
        path = WindowsPath(path_str)
        productpath = path.joinpath(productname)
        if not productpath.exists():
            productpath.mkdir(parents=True)
        
        return productpath
    
    def get_cache_directory(self) -> WindowsPath:
        """Get Windows AppData local directory"""
        path_str = environ.get('LocalAppData')
        if not path_str or not exists(path_str):
            raise RuntimeError('LocalAppData directory not found')
        
        path = WindowsPath(path_str)
        productpath = path.joinpath(productname)
        if not productpath.exists():
            productpath.mkdir(parents=True)
        
        return productpath
    
    def absolute_path(self, path_str: str) -> WindowsPath:
        """Create Windows-specific absolute Path object"""
        return WindowsPath(path_str).absolute()
    
    def create_game_detector(self) -> Optional[GameDetector]:
        """Create Windows game detector"""
        return WindowsGameDetector()