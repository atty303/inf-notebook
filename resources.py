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
