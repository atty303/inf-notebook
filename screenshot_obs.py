import numpy as np
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
        # OBS captures the source, then we crop the requested region using left/top offsets
        # This handles both full window capture and partial window capture scenarios
        import os
        import platform
        import uuid
        from pathlib import Path
        
        # Connect on first use if not already connected
        if not self.connected and obs_available:
            try:
                self.ws = obsws(self.host, self.port, self.password)
                self.ws.connect()
                self.connected = True
            except Exception as e:
                logger.error(f'Failed to connect to OBS WebSocket: {e}')
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
        
        if not self.connected or not self.ws:
            logger.warning(f'OBS not connected: connected={self.connected}, ws={self.ws is not None}, obs_available={obs_available}')
            return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
        
        try:
            # IMPORTANT: Using file save API instead of Base64 transfer
            # Base64 transfer takes ~0.8-0.9 seconds which is too slow for real-time capture
            # File save is much faster as it avoids Base64 encoding/decoding overhead
            
            # Create temporary file path using XDG cache on Linux or temp dir on Windows
            # This ensures compatibility with Flatpak OBS which has different /tmp sandbox
            if platform.system() == 'Linux':
                # Use XDG_CACHE_HOME or fallback to ~/.cache
                cache_dir = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
                cache_dir = cache_dir / 'inf-notebook'
                cache_dir.mkdir(parents=True, exist_ok=True)
                temp_path = str(cache_dir / f'obs_capture_{uuid.uuid4().hex}.bmp')
            else:
                # Windows: use user's temp directory
                import tempfile
                temp_dir = Path(tempfile.gettempdir())
                temp_path = str(temp_dir / f'obs_capture_{uuid.uuid4().hex}.bmp')
            
            # Save screenshot to file
            response = self.ws.call(requests.SaveSourceScreenshot(
                sourceName=self.source_name,
                imageFormat='bmp',
                imageFilePath=temp_path
            ))
            
            # Check if request was successful
            if hasattr(response, 'requestStatus') and not response.requestStatus.get('result', True):
                status = response.requestStatus
                logger.error(f'OBS request failed: code={status.get("code")}, comment={status.get("comment")}')
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            
            # Read image from file
            # Check if file exists and has content
            if not os.path.exists(temp_path):
                logger.error(f'Screenshot file not created at: {temp_path}')
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            
            file_size = os.path.getsize(temp_path)
            if file_size == 0:
                logger.error(f'Screenshot file is empty at: {temp_path}')
                os.unlink(temp_path)
                return np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
            
            image = Image.open(temp_path)
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            img_array = np.array(image)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f'Failed to delete temp file {temp_path}: {e}')
            
            # Crop the requested region from the captured source using left/top offsets
            # Ensure crop coordinates are within image bounds
            end_y = min(top + self.original_height, img_array.shape[0])
            end_x = min(left + self.original_width, img_array.shape[1])
            
            # Validate crop region
            if top >= 0 and left >= 0 and top < img_array.shape[0] and left < img_array.shape[1]:
                cropped = img_array[top:end_y, left:end_x]
                
                # Handle case where OBS minimum 8x8 size was used but we need original size
                if cropped.shape[0] < self.original_height or cropped.shape[1] < self.original_width:
                    result = np.zeros((self.original_height, self.original_width, 3), dtype=np.uint8)
                    result[:cropped.shape[0], :cropped.shape[1]] = cropped
                    final_result = result
                else:
                    # Ensure exact size match (in case captured size is larger than requested)
                    final_result = cropped[:self.original_height, :self.original_width]
                
                
                return final_result
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
