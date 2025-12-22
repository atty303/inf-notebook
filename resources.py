import os
import sys
import numpy as np
from logging import getLogger
import pickle
from os import rename,remove
from os.path import join,isfile,exists
from PIL import Image

logger_child_name = 'resources'

logger = getLogger().getChild(logger_child_name)
logger.debug(f'loaded resources.py')

from define import define

resources_dirname = 'resources'

sounds_dirname = 'sounds'
images_dirname = 'images'

sounds_dirpath = join(resources_dirname, sounds_dirname)
images_dirpath = join(resources_dirname, images_dirname)

sound_result_filepath = join(sounds_dirpath, 'result.wav')

images_resourcecheck_filepath = join(images_dirpath, 'resourcecheck.png')
images_summaryprocessing_filepath = join(images_dirpath, 'summaryprocessing.png')
images_imagenothing_filepath = join(images_dirpath, 'imagenothing.png')
images_graphnogenerate_filepath = join(images_dirpath, 'graphnogenerate.png')
images_loading_filepath = join(images_dirpath, 'loading.png')
images_stamp_filepath = join(images_dirpath, 'stamp.png')

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

        self.image_stamp = Image.open(images_stamp_filepath)

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
            # Check if musicselect is loaded
            if not hasattr(self, 'musicselect') or not self.musicselect:
                logger.warning('Musicselect not loaded, skipping fuzzy database build')
                return

            # Build binary databases for all categories
            categories = ['arcade', 'infinitas', 'leggendaria']
            total_built = 0

            for category in categories:
                category_config = self.musicselect.get('musicname', {}).get(category)
                if not category_config:
                    logger.warning(f'{category.title()} config not found, skipping')
                    continue

                # Build binary database using category-specific logic
                binary_db = self._convert_category_to_binary(category_config, category)

                # Store in musicselect structure
                if 'musicname' not in self.musicselect:
                    self.musicselect['musicname'] = {}
                self.musicselect['musicname'][f'{category}_binary'] = binary_db

                logger.info(f'{category.title()} fuzzy binary database built: {len(binary_db)} entries')
                total_built += len(binary_db)

            logger.info(f'Total fuzzy binary database entries built: {total_built}')

            # Build Result screen fuzzy databases
            self._build_result_fuzzy_database()

            # Build Details (options) fuzzy databases
            self._build_details_fuzzy_database()

        except Exception as e:
            logger.error(f'Failed to build fuzzy database: {e}')

    def _convert_category_to_binary(self, category_config, category):
        """Convert category config to binary database format for fuzzy matching"""
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

        # Process the category table
        if 'table' in category_config:
            process_table_recursive(category_config['table'])

        logger.debug(f'Converted {total_entries} entries to binary format')
        return binary_db

    def _build_result_fuzzy_database(self):
        """Build binary database for Result screen fuzzy recognition"""
        try:
            # Check if informations is loaded
            if not hasattr(self, 'informations') or not self.informations:
                logger.warning('Informations not loaded, skipping Result fuzzy database build')
                return

            result_total = 0

            # Note: Result music fuzzy recognition now uses exact-like approach with _try_fuzzy_table_traversal
            # No need for separate binary database for music recognition

            # Build fuzzy database for play_mode recognition
            if 'play_mode' in self.informations and 'table' in self.informations['play_mode']:
                binary_db = self._convert_result_simple_table_to_binary(self.informations['play_mode']['table'], 'play_mode')
                self.informations['play_mode']['binary'] = binary_db
                logger.info(f'Result play_mode fuzzy binary database built: {len(binary_db)} entries')
                result_total += len(binary_db)

            # Build fuzzy database for difficulty recognition
            if 'difficulty' in self.informations and 'table' in self.informations['difficulty']:
                difficulty_binary = {}
                difficulty_table = self.informations['difficulty']['table']

                # Convert difficulty color keys to binary
                if 'difficulty' in difficulty_table:
                    difficulty_binary['difficulty'] = self._convert_result_color_table_to_binary(difficulty_table['difficulty'], 'difficulty')
                    result_total += len(difficulty_binary['difficulty'])

                # Convert level tables to binary
                if 'level' in difficulty_table:
                    difficulty_binary['level'] = {}
                    for diff_name, level_table in difficulty_table['level'].items():
                        difficulty_binary['level'][diff_name] = self._convert_result_simple_table_to_binary(level_table, f'level_{diff_name}')
                        result_total += len(difficulty_binary['level'][diff_name])

                self.informations['difficulty']['binary'] = difficulty_binary
                logger.info(f'Result difficulty fuzzy binary database built: {result_total - (len(difficulty_binary.get("difficulty", {})))} entries')

            # Build fuzzy database for notes recognition
            if 'notes' in self.informations and 'table' in self.informations['notes']:
                binary_db = self._convert_result_simple_table_to_binary(self.informations['notes']['table'], 'notes')
                self.informations['notes']['binary'] = binary_db
                logger.info(f'Result notes fuzzy binary database built: {len(binary_db)} entries')
                result_total += len(binary_db)

            logger.info(f'Total Result fuzzy binary database entries built: {result_total}')

        except Exception as e:
            logger.error(f'Failed to build Result fuzzy database: {e}')

    # Note: _convert_result_music_table_to_binary is no longer needed
    # Result music fuzzy recognition now uses exact-like approach with _try_fuzzy_table_traversal

    def _convert_result_simple_table_to_binary(self, simple_table, table_type):
        """Convert simple hex key->value table to binary database"""
        import numpy as np

        binary_db = {}

        def hex_to_binary(hex_string: str) -> np.ndarray:
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

        for hex_key, value in simple_table.items():
            binary_key = hex_to_binary(hex_key)
            if len(binary_key) > 0:
                binary_db[hex_key] = {
                    'value': value,
                    'binary_key': binary_key,
                    'table_type': table_type
                }

        return binary_db

    def _convert_result_color_table_to_binary(self, color_table, table_type):
        """Convert RGB color key->value table to binary database"""
        import numpy as np

        binary_db = {}

        for color_key, value in color_table.items():
            try:
                # Convert color key (integer) to binary representation
                color_int = int(color_key)
                # Extract RGB components
                r = (color_int >> 16) & 0xFF
                g = (color_int >> 8) & 0xFF
                b = color_int & 0xFF

                # Create binary representation of RGB
                binary_key = np.array([r, g, b], dtype=np.uint8)

                binary_db[str(color_key)] = {
                    'value': value,
                    'binary_key': binary_key,
                    'rgb': (r, g, b),
                    'table_type': table_type
                }
            except (ValueError, TypeError):
                continue

        return binary_db

    def _build_details_fuzzy_database(self):
        """Build binary database for Details (options) fuzzy recognition"""
        try:
            # Check if details is loaded
            if not hasattr(self, 'details') or not self.details:
                logger.warning('Details not loaded, skipping Details fuzzy database build')
                return

            details_total = 0

            # Initialize details_binary structure
            if not hasattr(self, 'details_binary'):
                self.details_binary = {}

            # Build fuzzy database for options recognition
            if 'option' in self.details:
                option_binary = {}

                # Convert option keys to binary
                for hex_key, value in self.details['option'].items():
                    # Skip non-hex keys like 'lengths', 'width', etc.
                    if hex_key in ['lengths', 'width']:
                        continue

                    try:
                        # Convert hex key to binary
                        binary_key = self._hex_to_binary_array(hex_key)
                        if len(binary_key) > 0:
                            option_binary[hex_key] = {
                                'value': value,
                                'binary_key': binary_key,
                                'type': 'option'
                            }
                            details_total += 1
                    except (ValueError, TypeError):
                        continue

                self.details_binary['option'] = option_binary
                logger.info(f'Details option fuzzy binary database built: {len(option_binary)} entries')

            logger.info(f'Total Details fuzzy binary database entries built: {details_total}')

        except Exception as e:
            logger.error(f'Failed to build Details fuzzy database: {e}')

    def _hex_to_binary_array(self, hex_string):
        """Convert hex string to binary numpy array"""
        import numpy as np

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

    def load_resource_notesradar(self):
        resourcename = f'notesradar{define.notesradar_version}'

        self.notesradar: dict[str, dict[str, list[dict[str, str | int]]]] = load_resource_serialized(resourcename)

class ResourceTimestamp():
    def __init__(self, resourcename):
        self.resourcename = resourcename
        self.filepath = join(resources_dirname, f'{resourcename}.timestamp')

    def get_timestamp(self):
        if not exists(self.filepath):
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

def load_resource_serialized(resourcename: str) -> dict | None:
    '''リソースファイルをロードする

    もし一時ファイルが存在したら前回のダウンロードが失敗していたということなので、
    対象のファイルを削除して一時ファイルを元に戻す。

    Args:
        resourcename(str): 対象のリソース名
    Returns:
        dict or None: ロードされたリソースデータ
    '''
    filepath = join(resources_dirname, f'{resourcename}.res')
    filepath_tmp = join(resources_dirname, f'{resourcename}.res.tmp')

    if exists(filepath_tmp):
        if exists(filepath):
            remove(filepath)
        rename(filepath_tmp, filepath)

    if not isfile(filepath):
        return None

    with open(filepath, 'rb') as f:
        value = pickle.load(f)

    return value

def load_resource_numpy(resourcename):
    filepath = join(resources_dirname, f'{resourcename}.npy')
    return np.load(filepath)

def get_resource_filepath(filename):
    return join(resources_dirname, filename)

def check_latest(storage, filename) -> bool:
    '''対象のリソースファイルが最新かどうかをチェックする

    ローカルファイルとGCS上のファイルのタイムスタンプを比較して異なればダウンロードを試みる。
    ダウンロード開始前に現在のファイルを一時ファイルとしてファイル名を変更する。
    ダウンロードに成功した場合は、一時ファイルを削除する。
    もしダウンロードに失敗した場合、一時ファイルに戻す。

    Args:
        storage(): 対象のストレージ
        filename(str): 対象のファイル名
    Returns:
        bool: リソースファイルが更新された
    '''
    latest_timestamp: str | None = storage.get_resource_timestamp(filename)
    if latest_timestamp is None:
        return False

    filepath = join(resources_dirname, filename)

    timestamp = ResourceTimestamp(filename)
    local_timestamp: str | None = None
    if exists(filepath):
        local_timestamp = timestamp.get_timestamp()

    if local_timestamp == latest_timestamp:
        return False

    filepath_tmp = f'{filepath}.tmp'
    if exists(filepath):
        rename(filepath, filepath_tmp)

    if storage.download_resource(filename, filepath):
        logger.info(f'Download {filename}')
        timestamp.write_timestamp(latest_timestamp)

        if exists(filepath_tmp):
            remove(filepath_tmp)

        return True
    else:
        if exists(filepath):
            remove(filepath)

        rename(filepath_tmp, filepath)

        return False

resource = Resource()
