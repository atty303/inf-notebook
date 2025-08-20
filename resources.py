import os
import sys
import numpy as np
from logging import getLogger
import pickle
from os.path import isfile

logger_child_name = 'resources'

logger = getLogger().getChild(logger_child_name)
logger.debug(f'loaded resources.py')

from define import define

resources_dirname = 'resources'

sounds_dirname = 'sounds'
images_dirname = 'images'

sounds_dirpath = os.path.join(resources_dirname, sounds_dirname)
images_dirpath = os.path.join(resources_dirname, images_dirname)

sound_result_filepath = os.path.join(sounds_dirpath, 'result.wav')

images_resourcecheck_filepath = os.path.join(images_dirpath, 'resourcecheck.png')
images_summaryprocessing_filepath = os.path.join(images_dirpath, 'summaryprocessing.png')
images_imagenothing_filepath = os.path.join(images_dirpath, 'imagenothing.png')
images_graphnogenerate_filepath = os.path.join(images_dirpath, 'graphnogenerate.png')
images_loading_filepath = os.path.join(images_dirpath, 'loading.png')

class Resource():
    def __init__(self):
        self.fuzzy_search_enabled = False  # Will be set later by _build_fuzzy_database
        self.is_savable = load_resource_serialized('is_savable')
        self.play_side = load_resource_numpy('play_side')
        self.dead = load_resource_numpy('dead')
        self.rival = load_resource_numpy('rival')

        self.load_resource_informations()
        self.load_resource_details()
        self.load_resource_musictable()
        self.load_resource_musicselect()
        self.load_resource_notesradar()

        self.imagevalue_musictableinformation = None
    
    def load_resource_informations(self):
        resourcename = f'informations{define.informations_recognition_version}'
        
        self.informations = load_resource_serialized(resourcename)

    def load_resource_details(self):
        resourcename = f'details{define.details_recognition_version}'
        
        self.details = load_resource_serialized(resourcename)

    def load_resource_musictable(self):
        resourcename = f'musictable{define.musictable_version}'
        
        self.musictable = load_resource_serialized(resourcename)

    def load_resource_musicselect(self):
        resourcename = f'musicselect{define.musicselect_recognition_version}'
        
        self.musicselect = load_resource_serialized(resourcename)
        
        # Build fuzzy recognition binary database if enabled
        # Will be called later from main.pyw with setting instance
    
    def _build_fuzzy_database(self, setting_instance):
        """Build binary database for fuzzy recognition if enabled in settings"""
            
        self.fuzzy_search_enabled = setting_instance.get_value('fuzzy_search_enabled')
        if not self.fuzzy_search_enabled:
            logger.debug('Fuzzy search disabled in settings')
            return
        
        logger.info('Building fuzzy recognition binary database...')
        
        try:
            # Import fuzzy engine helper functions
            from fuzzy_recognition_engine import FuzzyRecognitionEngine
            
            # Get arcade configuration
            if not hasattr(self, 'musicselect') or not self.musicselect:
                logger.warning('Musicselect not loaded, skipping fuzzy database build')
                return
                
            arcade_config = self.musicselect.get('musicname', {}).get('arcade')
            if not arcade_config:
                logger.warning('Arcade config not found, skipping fuzzy database build')
                return
            
            # Build binary database using existing logic
            binary_db = self._convert_arcade_to_binary(arcade_config)
            
            # Store in musicselect structure
            if 'musicname' not in self.musicselect:
                self.musicselect['musicname'] = {}
            self.musicselect['musicname']['arcade_binary'] = binary_db
            
            logger.info(f'Fuzzy binary database built: {len(binary_db)} entries')
            
        except Exception as e:
            logger.error(f'Failed to build fuzzy database: {e}')
    
    def _convert_arcade_to_binary(self, arcade_config):
        """Convert arcade config to binary database format"""
        import numpy as np
        
        binary_db = {}
        total_entries = 0
        
        def hex_to_binary(hex_string: str) -> np.ndarray:
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
        
        def process_table_recursive(table, path=[]):
            nonlocal total_entries
            
            for key, value in table.items():
                if isinstance(value, str):
                    # Leaf node - song name
                    full_path = path + [key]
                    
                    # Convert all hex keys to binary
                    binary_path = []
                    for hex_key in full_path:
                        binary_key = hex_to_binary(hex_key)
                        binary_path.append(binary_key)
                    
                    # Store in binary database
                    db_key = '_'.join(full_path)
                    binary_db[db_key] = {
                        'song_name': value,
                        'binary_path': binary_path,
                        'hex_path': full_path,
                        'depth': len(full_path)
                    }
                    total_entries += 1
                    
                elif isinstance(value, dict):
                    process_table_recursive(value, path + [key])
        
        # Process the arcade table
        if 'table' in arcade_config:
            process_table_recursive(arcade_config['table'])
        
        logger.debug(f'Converted {total_entries} entries to binary format')
        return binary_db
    
    def load_resource_notesradar(self):
        resourcename = f'notesradar{define.notesradar_version}'
        
        self.notesradar: dict[str, dict[str, list[dict[str, str | int]]]] = load_resource_serialized(resourcename)

class ResourceTimestamp():
    def __init__(self, resourcename):
        self.resourcename = resourcename
        self.filepath = os.path.join(resources_dirname, f'{resourcename}.timestamp')
    
    def get_timestamp(self):
        if not os.path.exists(self.filepath):
            return None
        with open(self.filepath, 'r') as f:
            timestamp = f.read()

        return timestamp

    def write_timestamp(self, timestamp):
        logger.info(f'Update timestamp {self.resourcename} {timestamp}')
        with open(self.filepath, 'w') as f:
            f.write(timestamp)

def play_sound_result():
    if os.path.exists(sound_result_filepath):
        try:
            if sys.platform == 'win32':
                import winsound
                winsound.PlaySound(sound_result_filepath, winsound.SND_FILENAME)
            elif sys.platform == 'darwin':
                os.system(f'afplay "{sound_result_filepath}"')
            else:  # Linux and other Unix-like systems
                # Try multiple commands in order of preference
                if os.system('which pw-play >/dev/null 2>&1') == 0:
                    os.system(f'pw-play "{sound_result_filepath}"')
                elif os.system('which paplay >/dev/null 2>&1') == 0:
                    os.system(f'paplay "{sound_result_filepath}"')
                elif os.system('which aplay >/dev/null 2>&1') == 0:
                    os.system(f'aplay -q "{sound_result_filepath}"')
                else:
                    logger.warning('No suitable audio player found on Linux')
        except Exception as e:
            logger.error(f'Failed to play sound: {e}')

def load_resource_serialized(resourcename):
    filepath = os.path.join(resources_dirname, f'{resourcename}.res')
    if not isfile(filepath):
        return None
    
    with open(filepath, 'rb') as f:
        value = pickle.load(f)
    
    return value

def load_resource_numpy(resourcename):
    filepath = os.path.join(resources_dirname, f'{resourcename}.npy')
    return np.load(filepath)

def get_resource_filepath(filename):
    return os.path.join(resources_dirname, filename)

def check_latest(storage, filename):
    timestamp = ResourceTimestamp(filename)

    latest_timestamp = storage.get_resource_timestamp(filename)
    if latest_timestamp is None:
        return False
    
    local_timestamp = timestamp.get_timestamp()

    if local_timestamp == latest_timestamp:
        return False
    
    filepath = os.path.join(resources_dirname, filename)
    if storage.download_resource(filename, filepath):
        logger.info(f'Download {filename}')
        timestamp.write_timestamp(latest_timestamp)
        return True

resource = Resource()
