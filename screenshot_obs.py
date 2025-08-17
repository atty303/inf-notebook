import numpy as np
import base64
import io
from PIL import Image
from logging import getLogger

logger = getLogger().getChild('screenshot_obs')

try:
    from obswebsocket import obsws, requests
    obs_available = True
    
    # Disable obswebsocket DEBUG logging to avoid huge Base64 logs
    import logging
    logging.getLogger('obswebsocket.core').setLevel(logging.INFO)
    
except ImportError:
    logger.warning('obswebsocket not installed. Install with: pip install obs-websocket-py')
    obs_available = False
    obsws = None
    requests = None

class OBSCapture:
    def __init__(self, width, height, host='localhost', port=4455, password='', source_name='Game Capture'):
        # OBS requires minimum 8x8 pixels for screenshots
        self.width = max(width, 8)
        self.height = max(height, 8)
        self.original_width = width
        self.original_height = height
        if width < 8 or height < 8:
            pass
        self.source_name = source_name
        self.ws = None
        self.connected = False
        
        # Defer connection until first screenshot request
        self.host = host
        self.port = port
        self.password = password
    
    def shot(self, left, top):
        
        # Connect on first use if not already connected
        if not self.connected and obs_available:
            logger.info(f'Attempting OBS WebSocket connection to {self.host}:{self.port}')
            try:
                self.ws = obsws(self.host, self.port, self.password)
                self.ws.connect()
                self.connected = True
                logger.info(f'Successfully connected to OBS WebSocket at {self.host}:{self.port}')
                logger.info(f'Using OBS source: {self.source_name}')
            except Exception as e:
                logger.error(f'Failed to connect to OBS WebSocket: {e}')
                logger.info('Make sure OBS is running with WebSocket server enabled')
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
        
        if not self.connected or not self.ws:
            logger.warning(f'OBS not connected: connected={self.connected}, ws={self.ws is not None}, obs_available={obs_available}')
            return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
        
        try:
            # For OBS, get full screen via Base64 and crop the region we need
            response = self.ws.call(requests.GetSourceScreenshot(
                sourceName=self.source_name,
                imageFormat='png'
                # Don't specify width/height to get full source size
            ))
            
            # Check if request was successful
            if hasattr(response, 'requestStatus') and not response.requestStatus.get('result', True):
                status = response.requestStatus
                logger.error(f'OBS request failed: code={status.get("code")}, comment={status.get("comment")}')
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            
            # Get image data from response
            try:
                image_data = response.getImageData()
                if not image_data:
                    logger.error(f'Empty imageData in OBS response for source: {self.source_name}')
                    return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            except (KeyError, AttributeError) as e:
                logger.error(f'No imageData in OBS response for source: {self.source_name} - {e}')
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            
            # Don't log image data length to avoid huge logs
            
            if image_data.startswith('data:image/png;base64,'):
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_array = np.array(image)
            
            # Crop the requested region from the full screenshot
            end_y = min(top + self.original_height, img_array.shape[0])
            end_x = min(left + self.original_width, img_array.shape[1])
            
            if top >= 0 and left >= 0 and top < img_array.shape[0] and left < img_array.shape[1]:
                cropped = img_array[top:end_y, left:end_x]
                
                # Ensure we have the exact size requested (pad with zeros if needed)
                if cropped.shape[0] < self.original_height or cropped.shape[1] < self.original_width:
                    result = np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
                    result[:cropped.shape[0], :cropped.shape[1]] = cropped
                    return result
                
                return cropped[:self.original_height, :self.original_width]
            else:
                logger.warning(f'Crop region [{top}:{end_y}, {left}:{end_x}] is outside image bounds {img_array.shape}')
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            
        except Exception as e:
            logger.error(f'Failed to capture screenshot from OBS: {e}')
            logger.error(f'Source: {self.source_name}, Size: {self.original_width}x{self.original_height}')
            import traceback
            logger.error(f'Traceback: {traceback.format_exc()}')
            return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
    
    def __del__(self):
        if self.ws:
            try:
                self.ws.disconnect()
            except:
                pass
