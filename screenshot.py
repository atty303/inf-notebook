import platform
from datetime import datetime
from PIL import Image
from logging import getLogger
from os.path import exists, basename
import numpy as np

logger_child_name = 'screenshot'

logger = getLogger().getChild(logger_child_name)
logger.debug('loaded screenshot.py')

from define import define
from resources import load_resource_serialized

class Screen:
    def __init__(self, np_value, filename):
        self.np_value = np_value
        
        self.original = Image.fromarray(np_value)
        self.filename = filename

class Screenshot:
    xy = None
    screentable = load_resource_serialized('get_screen')
    np_value = None

    def __init__(self, use_obs=False, obs_host='localhost', obs_port=4455, obs_password='', obs_source_name='Game Capture'):
        """
        Initialize Screenshot with either OBS or Windows API backend
        
        Args:
            use_obs: Whether to use OBS WebSocket for capture
            obs_host: OBS WebSocket server host
            obs_port: OBS WebSocket server port
            obs_password: OBS WebSocket server password
            obs_source_name: OBS source name to capture from
        """
        self.use_obs = use_obs
        
        if use_obs:
            from screenshot_obs import OBSCapture
            logger.info('Using OBS WebSocket for screenshot capture')
            self.checkscreens = [
                (screen, (areas['left'], areas['top']), 
                 OBSCapture(areas['width'], areas['height'], obs_host, obs_port, obs_password, obs_source_name), 
                 self.screentable[screen]) 
                for screen, areas in define.screens.items()
            ]
            self.capture = OBSCapture(define.width, define.height, obs_host, obs_port, obs_password, obs_source_name)
            # For OBS, we don't need window position detection
            self.xy = (0, 0)
        else:
            # Check platform for appropriate capture method
            if platform.system() == 'Windows':
                from screenshot_windows import WindowsCapture
                logger.info('Using Windows API for screenshot capture')
                Capture = WindowsCapture
            else:
                # Linux without OBS - use dummy capture
                logger.warning('No capture method available for Linux without OBS')
                class DummyCapture:
                    def __init__(self, width, height):
                        self.width = width
                        self.height = height
                    
                    def shot(self, left, top):
                        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
                    
                    def __del__(self):
                        pass
                
                Capture = DummyCapture
            
            self.checkscreens = [
                (screen, (areas['left'], areas['top']), 
                 Capture(areas['width'], areas['height']), 
                 self.screentable[screen]) 
                for screen, areas in define.screens.items()
            ]
            self.capture = Capture(define.width, define.height)
            
            # For Linux without OBS, set default position
            if platform.system() == 'Linux':
                self.xy = (0, 0)

    def __del__(self):
        for screen, pos, capture, value in self.checkscreens:
            del capture
        del self.capture

    def get_screen(self):
        if self.xy is None:
            return None
        
        results = []
        for screen, pos, capture, value in self.checkscreens:
            x = self.xy[0] + pos[0]
            y = self.xy[1] + pos[1]

            if np.sum(capture.shot(x, y)) == value:
                results.append(screen)
        
        if len(results) != 1:
            return None

        return results[0]

    def shot(self):
        if self.xy is None:
            return False
        
        self.np_value = self.capture.shot(self.xy[0], self.xy[1])[::-1, :, ::-1]
        return True

    def get_image(self):
        if self.np_value is None:
            return None
        
        return Image.fromarray(self.np_value)

    def get_resultscreen(self):
        now = datetime.now()
        filename = f"{now.strftime('%Y%m%d-%H%M%S-%f')}.png"

        return Screen(self.np_value, filename)

def open_screenimage(filepath):
    if not exists(filepath):
        return None
    
    image = Image.open(filepath).convert('RGB')
    filename = basename(filepath)

    return Screen(np.array(image), filename)