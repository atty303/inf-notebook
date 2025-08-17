import numpy as np
import base64
import io
from PIL import Image
from logging import getLogger

logger = getLogger().getChild('screenshot_obs')

try:
    from obswebsocket import obsws, requests
    obs_available = True
except ImportError:
    logger.warning('obswebsocket not installed. Install with: pip install obs-websocket-py')
    obs_available = False
    obsws = None
    requests = None

class OBSCapture:
    def __init__(self, width, height, host='localhost', port=4455, password='', source_name='Game Capture'):
        self.width = width
        self.height = height
        self.source_name = source_name
        self.ws = None
        self.connected = False
        
        if obs_available:
            try:
                self.ws = obsws(host, port, password)
                self.ws.connect()
                self.connected = True
                logger.info(f'Connected to OBS WebSocket at {host}:{port}')
                logger.info(f'Using OBS source: {source_name}')
            except Exception as e:
                logger.error(f'Failed to connect to OBS WebSocket: {e}')
                logger.info('Make sure OBS is running with WebSocket server enabled')
    
    def shot(self, left, top):
        if not self.connected or not self.ws:
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        try:
            response = self.ws.call(requests.GetSourceScreenshot(
                sourceName=self.source_name,
                imageFormat='png',
                imageWidth=self.width,
                imageHeight=self.height
            ))
            
            image_data = response.getImageData()
            if image_data.startswith('data:image/png;base64,'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_array = np.array(image)
            
            if left > 0 or top > 0:
                full_image = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                full_image[top:top+img_array.shape[0], left:left+img_array.shape[1]] = img_array
                return full_image
            
            return img_array[:self.height, :self.width]
            
        except Exception as e:
            logger.error(f'Failed to capture screenshot from OBS: {e}')
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
    
    def __del__(self):
        if self.ws:
            try:
                self.ws.disconnect()
            except:
                pass
        logger.debug('Called OBS Screenshot destructor.')