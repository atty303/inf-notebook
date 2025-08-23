import numpy as np
from logging import getLogger

logger_child_name = 'recog'

logger = getLogger().getChild(logger_child_name)
logger.debug('loaded recog.py')

from define import define
from resources import resource
from result import ResultInformations,ResultValues,ResultDetails,ResultOptions,Result

class Recognition():
    class Result():
        @staticmethod
        def get_play_side(np_value):
            for target in define.value_list['play_sides']:
                trimmed = np_value[define.areas_np['play_side'][target]]
                if np.all((resource.play_side==0)|(trimmed==resource.play_side)):
                    return target

            # === FUZZY RECOGNITION FOR RESULT PLAY_SIDE (new addition) ===
            if resource.fuzzy_search_enabled:
                result = Recognition.Result._try_play_side_fuzzy_recognition(np_value)
                if result:
                    return result
                
                # Save failed recognition for debugging
                Recognition.Result._save_failed_play_side_recognition(np_value)

            return None

        @staticmethod
        def get_has_dead(np_value, play_side):
            trimmed = np_value[define.areas_np['dead'][play_side]]
            if np.all((resource.dead==0)|(trimmed==resource.dead)):
                return True
            else:
                # === FUZZY RECOGNITION FOR RESULT HAS_DEAD (new addition) ===
                if resource.fuzzy_search_enabled:
                    result = Recognition.Result._try_has_dead_fuzzy_recognition(np_value, play_side)
                    if result is not None:
                        return result
                
                return False
        
        @staticmethod
        def get_has_rival(np_value):
            trimmed = np_value[define.areas_np['rival']]
            if np.all((resource.rival==0)|(trimmed==resource.rival)):
                return True
            else:
                # === FUZZY RECOGNITION FOR RESULT HAS_RIVAL (new addition) ===
                if resource.fuzzy_search_enabled:
                    result = Recognition.Result._try_has_rival_fuzzy_recognition(np_value)
                    if result is not None:
                        return result
                
                return False
        
        @staticmethod
        def get_play_mode(np_value_informations):
            if resource.informations is None:
                return None
            
            trimmed = np_value_informations[resource.informations['play_mode']['trim']].flatten()
            bins = np.where(trimmed==resource.informations['play_mode']['maskvalue'], 1, 0)
            hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
            tablekey = ''.join([format(v, '0x') for v in hexs])
            if not tablekey in resource.informations['play_mode']['table'].keys():
                # === FUZZY RECOGNITION FOR RESULT PLAY_MODE (new addition) ===
                if resource.fuzzy_search_enabled:
                    result = Recognition.Result._try_play_mode_fuzzy_recognition(np_value_informations)
                    if result:
                        return result
                    
                    # Save failed recognition for debugging
                    Recognition.Result._save_failed_play_mode_recognition(np_value_informations)
                
                return None
            return resource.informations['play_mode']['table'][tablekey]

        @staticmethod
        def get_difficulty(np_value_informations):
            if resource.informations is None:
                return None, None
            
            trimmed = np_value_informations[resource.informations['difficulty']['trim']]
            converted = trimmed[:,:,0]*0x10000+trimmed[:,:,1]*0x100+trimmed[:,:,2]

            uniques, counts = np.unique(converted, return_counts=True)
            difficultykey = uniques[np.argmax(counts)]
            if not difficultykey in resource.informations['difficulty']['table']['difficulty'].keys():
                return None, None
            
            difficulty = resource.informations['difficulty']['table']['difficulty'][difficultykey]

            leveltrimmed = converted[resource.informations['difficulty']['trimlevel']].flatten()
            bins = np.where(leveltrimmed==difficultykey, 1, 0)
            hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
            levelkey = ''.join([format(v, '0x') for v in hexs])

            if not levelkey in resource.informations['difficulty']['table']['level'][difficulty].keys():
                return None, None
            
            level = resource.informations['difficulty']['table']['level'][difficulty][levelkey]

            return difficulty, level
            
            # === FUZZY RECOGNITION FOR RESULT DIFFICULTY (new addition) ===
            if resource.fuzzy_search_enabled:
                result = Recognition.Result._try_difficulty_fuzzy_recognition(np_value_informations)
                if result:
                    return result
                
                # Save failed recognition for debugging
                Recognition.Result._save_failed_difficulty_recognition(np_value_informations)
            
            return None, None

        @staticmethod
        def get_notes(np_value_informations):
            if resource.informations is None:
                return None
            
            trimmed = np_value_informations[resource.informations['notes']['trim']]
            splited = np.hsplit(trimmed, resource.informations['notes']['digit'])

            value = 0
            pos = 3
            for pos in range(4):
                trimmed_once = splited[pos][resource.informations['notes']['trimnumber']]
                bins = np.where(trimmed_once==resource.informations['notes']['maskvalue'], 1, 0).flatten()
                hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs])
                if not tablekey in resource.informations['notes']['table'].keys():
                    # === FUZZY RECOGNITION FOR RESULT NOTES (new addition) ===
                    if resource.fuzzy_search_enabled:
                        digit_result = Recognition.Result._try_notes_digit_fuzzy_recognition(trimmed_once, pos)
                        if digit_result is not None:
                            value = value * 10 + digit_result
                            continue
                    
                    if value != 0:
                        # Save failed recognition for debugging
                        if resource.fuzzy_search_enabled:
                            Recognition.Result._save_failed_notes_recognition(np_value_informations)
                        return None
                    else:
                        continue
                
                value = value * 10 + resource.informations['notes']['table'][tablekey]

            if value == 0:
                return None

            return value

        @staticmethod
        def get_music(np_value_informations):
            '''曲名を取得する

            Args:
                np_value_informations (np.array): 対象のトリミングされたリザルト画像データ

            Returns:
                str: 曲名(認識失敗時はNone)
            '''
            if resource.informations is None:
                return None

            trimmed = np_value_informations[resource.informations['music']['trim']]

            lower = resource.informations['music']['factors']['blue']['lower']
            upper = resource.informations['music']['factors']['blue']['upper']
            filtereds = []
            for i in range(trimmed.shape[2]):
                filtereds.append(np.where((lower[:,:,i]<=trimmed[:,:,i])&(trimmed[:,:,i]<=upper[:,:,i]), trimmed[:,:,i], 0))
            blue = np.where((filtereds[0]!=0)&(filtereds[1]!=0)&(filtereds[2]!=0), filtereds[2], 0)

            lower = resource.informations['music']['factors']['red']['lower']
            upper = resource.informations['music']['factors']['red']['upper']
            filtereds = []
            for i in range(trimmed.shape[2]):
                filtereds.append(np.where((lower[:,:,i]<=trimmed[:,:,i])&(trimmed[:,:,i]<=upper[:,:,i]), trimmed[:,:,i], 0))
            red = np.where((filtereds[0]!=0)&(filtereds[1]!=0)&(filtereds[2]!=0), trimmed[:,:,0], 0)

            lower = resource.informations['music']['factors']['gray']['lower']
            upper = resource.informations['music']['factors']['gray']['upper']
            filtereds = []
            for i in range(trimmed.shape[2]):
                filtereds.append(np.where((lower[:,:,i]<=trimmed[:,:,i])&(trimmed[:,:,i]<=upper[:,:,i]), trimmed[:,:,i], 0))
            gray = np.where((filtereds[0]==filtereds[1])&(filtereds[0]==filtereds[2]), filtereds[0], 0)

            gray_count = np.count_nonzero(gray)
            blue_count = np.count_nonzero(blue)
            red_count = np.count_nonzero(red)
            max_count = max(gray_count, blue_count, red_count)
            if max_count == gray_count:
                masked = np.where(resource.informations['music']['masks']['gray']==1,gray,0)
                targettable = resource.informations['music']['tables']['gray']
            if max_count == blue_count:
                masked = np.where(resource.informations['music']['masks']['blue']==1,blue,0)
                targettable = resource.informations['music']['tables']['blue']
            if max_count == red_count:
                masked = np.where(resource.informations['music']['masks']['red']==1,red,0)
                targettable = resource.informations['music']['tables']['red']
            
            for height in range(masked.shape[0]):
                unique, counts = np.unique(masked[height], return_counts=True)
                if len(unique) > 1:
                    index = -np.argmax(np.flip(counts[1:])) - 1
                    intensity = unique[index]
                    bins = np.where(masked[height]==intensity, 1, 0)
                    hexs = bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                    tablekey = f"{height:02d}{''.join([format(v, '0x') for v in hexs])}"
                else:
                    tablekey = f'{height:02d}'
                if not tablekey in targettable.keys():
                    break

                if type(targettable[tablekey]) == str:
                    return targettable[tablekey]
                
                targettable = targettable[tablekey]
            
            # === FUZZY RECOGNITION FOR RESULT MUSIC (new addition) ===
            if resource.fuzzy_search_enabled:
                # Save input image for debugging when fuzzy recognition is needed
                Recognition.Result._save_music_input_for_debug(np_value_informations)
                
                # Try threshold tolerance strategy first
                result = Recognition.Result._try_music_threshold_tolerance(np_value_informations, tolerance=10)
                if result:
                    return result
                
                # Try fuzzy binary matching if threshold tolerance fails
                result = Recognition.Result._try_music_fuzzy_recognition(np_value_informations)
                if result:
                    return result
                
                # Save failed recognition for debugging
                Recognition.Result._save_failed_music_recognition(np_value_informations)
            
            return None

        @staticmethod
        def _try_music_threshold_tolerance(np_value_informations, tolerance=10):
            '''Threshold tolerance strategy for Result music recognition'''
            if resource.informations is None:
                return None

            trimmed = np_value_informations[resource.informations['music']['trim']]

            # Try each color with expanded threshold tolerance
            colors = ['blue', 'red', 'gray']
            best_result = None
            
            for color in colors:
                # Get original thresholds and expand them
                lower = resource.informations['music']['factors'][color]['lower']
                upper = resource.informations['music']['factors'][color]['upper']
                
                # Apply tolerance to thresholds
                expanded_lower = np.maximum(0, lower - tolerance)
                expanded_upper = np.minimum(255, upper + tolerance)
                
                filtereds = []
                for i in range(trimmed.shape[2]):
                    filtereds.append(np.where((expanded_lower[:,:,i]<=trimmed[:,:,i])&(trimmed[:,:,i]<=expanded_upper[:,:,i]), trimmed[:,:,i], 0))
                
                if color == 'blue':
                    masked_color = np.where((filtereds[0]!=0)&(filtereds[1]!=0)&(filtereds[2]!=0), filtereds[2], 0)
                elif color == 'red':
                    masked_color = np.where((filtereds[0]!=0)&(filtereds[1]!=0)&(filtereds[2]!=0), trimmed[:,:,0], 0)
                else:  # gray
                    masked_color = np.where((filtereds[0]==filtereds[1])&(filtereds[0]==filtereds[2]), filtereds[0], 0)

                # Check if this color has enough pixels
                if np.count_nonzero(masked_color) == 0:
                    continue
                
                # Try recognition with this color
                masked = np.where(resource.informations['music']['masks'][color]==1, masked_color, 0)
                targettable = resource.informations['music']['tables'][color]
                
                result = Recognition.Result._try_table_recognition(masked, targettable)
                if result:
                    return result
            
            return None

        @staticmethod
        def _try_table_recognition(masked, targettable):
            '''Helper method to traverse hierarchical table recognition'''
            for height in range(masked.shape[0]):
                unique, counts = np.unique(masked[height], return_counts=True)
                if len(unique) > 1:
                    index = -np.argmax(np.flip(counts[1:])) - 1
                    intensity = unique[index]
                    bins = np.where(masked[height]==intensity, 1, 0)
                    hexs = bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                    tablekey = f"{height:02d}{''.join([format(v, '0x') for v in hexs])}"
                else:
                    tablekey = f'{height:02d}'
                
                if not tablekey in targettable.keys():
                    break

                if type(targettable[tablekey]) == str:
                    return targettable[tablekey]
                
                targettable = targettable[tablekey]
            
            return None

        @staticmethod
        def _try_music_fuzzy_recognition(np_value_informations):
            '''Fuzzy matching for Result music recognition using exact-like approach'''
            if resource.informations is None:
                return None
            
            import numpy as np
            
            trimmed = np_value_informations[resource.informations['music']['trim']]
            
            # Try each color - same as exact matching
            colors = ['blue', 'red', 'gray']
            for color in colors:
                # Extract color-specific features using original logic
                lower = resource.informations['music']['factors'][color]['lower']
                upper = resource.informations['music']['factors'][color]['upper']
                
                filtereds = []
                for i in range(trimmed.shape[2]):
                    filtereds.append(np.where((lower[:,:,i]<=trimmed[:,:,i])&(trimmed[:,:,i]<=upper[:,:,i]), trimmed[:,:,i], 0))
                
                if color == 'blue':
                    masked_color = np.where((filtereds[0]!=0)&(filtereds[1]!=0)&(filtereds[2]!=0), filtereds[2], 0)
                elif color == 'red':
                    masked_color = np.where((filtereds[0]!=0)&(filtereds[1]!=0)&(filtereds[2]!=0), trimmed[:,:,0], 0)
                else:  # gray
                    masked_color = np.where((filtereds[0]==filtereds[1])&(filtereds[0]==filtereds[2]), filtereds[0], 0)

                if np.count_nonzero(masked_color) == 0:
                    continue
                
                # Apply mask
                masked = np.where(resource.informations['music']['masks'][color]==1, masked_color, 0)
                
                # Try fuzzy hierarchical table traversal - same as exact but with tolerance
                targettable = resource.informations['music']['tables'][color]
                result = Recognition.Result._try_fuzzy_table_traversal(masked, targettable)
                if result:
                    return result
            
            return None

        @staticmethod
        def _try_fuzzy_table_traversal(masked, targettable, max_bit_errors=50):
            '''Fuzzy hierarchical table traversal with multiple path exploration'''
            import numpy as np
            from heapq import heappush, heappop
            
            def calculate_key_distance(tablekey, dbkey):
                """Calculate distance between tablekey and database key"""
                # Keys must have the same row number prefix (first 2 chars)
                if len(tablekey) < 2 or len(dbkey) < 2 or tablekey[:2] != dbkey[:2]:
                    return float('inf')
                
                # Get hex portions
                hex1 = tablekey[2:] if len(tablekey) > 2 else ''
                hex2 = dbkey[2:] if len(dbkey) > 2 else ''
                
                try:
                    # Handle case where DB stores "07" for all-zeros
                    if hex1 and not hex2:
                        # tablekey has hex, dbkey doesn't (implies all zeros in DB)
                        bin1 = bin(int(hex1, 16))[2:].zfill(len(hex1) * 4)
                        bin2 = '0' * len(bin1)  # All zeros
                    elif hex2 and not hex1:
                        # dbkey has hex, tablekey doesn't (implies all zeros in query)
                        bin2 = bin(int(hex2, 16))[2:].zfill(len(hex2) * 4)
                        bin1 = '0' * len(bin2)  # All zeros
                    elif hex1 and hex2:
                        # Both have hex - must be same length
                        if len(hex1) != len(hex2):
                            return float('inf')
                        bin1 = bin(int(hex1, 16))[2:].zfill(len(hex1) * 4)
                        bin2 = bin(int(hex2, 16))[2:].zfill(len(hex2) * 4)
                    else:
                        # Both are just row numbers (e.g., "07" == "07")
                        return 0
                    
                    return sum(c1 != c2 for c1, c2 in zip(bin1, bin2)) if bin1 else 0
                except:
                    return float('inf')
            
            def generate_query_keys(masked):
                """Generate query keys for each row"""
                query_keys = []
                for height in range(masked.shape[0]):
                    unique, counts = np.unique(masked[height], return_counts=True)
                    if len(unique) > 1:
                        index = -np.argmax(np.flip(counts[1:])) - 1
                        intensity = unique[index]
                        bins = np.where(masked[height]==intensity, 1, 0)
                        hexs = bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                        tablekey = f"{height:02d}{''.join([format(v, '0x') for v in hexs])}"
                    else:
                        tablekey = f'{height:02d}'
                    query_keys.append(tablekey)
                return query_keys
            
            def explore_paths(query_keys, table, max_total_distance=max_bit_errors):
                """Explore all possible paths and find the best matching song"""
                # Priority queue: (total_distance, depth, unique_id, current_table, path_taken)
                pq = [(0, 0, 0, table, [])]
                best_result = None
                best_distance = float('inf')
                unique_id = 0
                
                while pq:
                    total_distance, depth, _, current_table, path_taken = heappop(pq)
                    
                    # If we've processed all query keys, we should have found a result
                    if depth >= len(query_keys):
                        continue
                    
                    # Early termination if distance is too high
                    if total_distance > max_total_distance:
                        continue
                    
                    query_key = query_keys[depth]
                    
                    # Try all keys in current table level
                    for db_key, value in current_table.items():
                        key_distance = calculate_key_distance(query_key, db_key)
                        if key_distance == float('inf'):
                            continue
                        
                        new_total_distance = total_distance + key_distance
                        if new_total_distance > max_total_distance:
                            continue
                        
                        new_path = path_taken + [db_key]
                        
                        if isinstance(value, str):
                            # Found a song - check if it's the best so far
                            if new_total_distance < best_distance:
                                best_distance = new_total_distance
                                best_result = value
                        elif isinstance(value, dict):
                            # Continue exploring this path
                            unique_id += 1
                            heappush(pq, (new_total_distance, depth + 1, unique_id, value, new_path))
                
                return best_result, best_distance
            
            # Generate query keys from the masked image
            query_keys = generate_query_keys(masked)
            
            # Explore all paths and find the best match
            result, distance = explore_paths(query_keys, targettable)
            
            return result

        # Note: _extract_binary_path_from_masked and _fuzzy_search_result_music are no longer needed
        # Result music fuzzy recognition now uses exact-like approach with _try_fuzzy_table_traversal

        @staticmethod
        def _save_music_input_for_debug(np_value_informations):
            '''Save Result music input image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            import numpy as np
            
            try:
                # Create debug directory
                debug_dir = os.path.join('debug_results', 'music_input')
                os.makedirs(debug_dir, exist_ok=True)
                
                # Generate timestamp filename
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'input_{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                # Convert numpy array to PIL Image and save
                # np_value_informations is BGR format from OpenCV, convert to RGB
                rgb_image = np_value_informations[:, :, ::-1]  # BGR to RGB
                img = Image.fromarray(rgb_image.astype('uint8'), 'RGB')
                img.save(filepath)
                
                print(f"[DEBUG] Saved Result music input image: {filepath}")
                
            except Exception as e:
                print(f"[DEBUG] Failed to save Result music input image: {e}")

        @staticmethod
        def _save_failed_music_recognition(np_value_informations):
            '''Save failed music recognition image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            
            try:
                # Create debug directory
                debug_dir = os.path.join('failed_results', 'music')
                os.makedirs(debug_dir, exist_ok=True)
                
                # Generate timestamp filename
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                # Extract music recognition area
                if resource.informations and 'music' in resource.informations:
                    trimmed = np_value_informations[resource.informations['music']['trim']]
                    # Convert numpy array to PIL Image
                    img = Image.fromarray(trimmed.astype('uint8'))
                    img.save(filepath)
                    
            except Exception as e:
                # Silently ignore save errors to prevent disrupting main recognition
                pass

        @staticmethod
        def _try_difficulty_fuzzy_recognition(np_value_informations):
            '''Fuzzy recognition for Result difficulty'''
            if resource.informations is None or 'binary' not in resource.informations.get('difficulty', {}):
                return None
                
            import numpy as np
            
            trimmed = np_value_informations[resource.informations['difficulty']['trim']]
            converted = trimmed[:,:,0]*0x10000+trimmed[:,:,1]*0x100+trimmed[:,:,2]

            # Try difficulty recognition with color tolerance
            uniques, counts = np.unique(converted, return_counts=True)
            
            # Try multiple candidate colors (top 3 most frequent)
            sorted_indices = np.argsort(counts)[::-1]
            candidates = uniques[sorted_indices[:3]]
            
            difficulty_binary_db = resource.informations['difficulty']['binary'].get('difficulty', {})
            
            for candidate_color in candidates:
                # Try exact match first
                if str(candidate_color) in resource.informations['difficulty']['table']['difficulty']:
                    difficulty = resource.informations['difficulty']['table']['difficulty'][str(candidate_color)]
                    
                    # Try level recognition
                    level = Recognition.Result._try_level_recognition_with_tolerance(converted, candidate_color, difficulty)
                    if level:
                        return difficulty, level
                
                # Try fuzzy color matching
                result = Recognition.Result._try_fuzzy_color_match(candidate_color, difficulty_binary_db, tolerance=10)
                if result:
                    difficulty = result['value']
                    level = Recognition.Result._try_level_recognition_with_tolerance(converted, candidate_color, difficulty)
                    if level:
                        return difficulty, level
            
            return None
        
        @staticmethod
        def _try_fuzzy_color_match(target_color, binary_db, tolerance=10):
            '''Fuzzy match RGB color with tolerance'''
            import numpy as np
            
            # Extract target RGB
            target_r = (target_color >> 16) & 0xFF
            target_g = (target_color >> 8) & 0xFF
            target_b = target_color & 0xFF
            target_rgb = np.array([target_r, target_g, target_b])
            
            best_match = None
            min_distance = float('inf')
            
            for color_key, entry in binary_db.items():
                stored_rgb = np.array(entry['rgb'])
                
                # Calculate color distance
                color_distance = np.sum(np.abs(target_rgb - stored_rgb))
                
                if color_distance <= tolerance * 3:  # tolerance per channel
                    if color_distance < min_distance:
                        min_distance = color_distance
                        best_match = entry
            
            return best_match
        
        @staticmethod
        def _try_level_recognition_with_tolerance(converted, difficulty_color, difficulty_name):
            '''Try level recognition with tolerance'''
            import numpy as np
            
            leveltrimmed = converted[resource.informations['difficulty']['trimlevel']].flatten()
            
            # Try exact match first
            bins = np.where(leveltrimmed==difficulty_color, 1, 0)
            hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
            levelkey = ''.join([format(v, '0x') for v in hexs])
            
            level_table = resource.informations['difficulty']['table']['level'].get(difficulty_name, {})
            if levelkey in level_table:
                return level_table[levelkey]
            
            # Try with tolerance (allow slight color variations)
            for tolerance in [1, 2, 5, 10]:
                for offset in range(-tolerance, tolerance + 1):
                    test_color = difficulty_color + offset
                    bins = np.where(leveltrimmed==test_color, 1, 0)
                    hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                    test_levelkey = ''.join([format(v, '0x') for v in hexs])
                    
                    if test_levelkey in level_table:
                        return level_table[test_levelkey]
            
            # Try fuzzy binary matching if available
            if 'binary' in resource.informations['difficulty'] and 'level' in resource.informations['difficulty']['binary']:
                level_binary_db = resource.informations['difficulty']['binary']['level'].get(difficulty_name, {})
                if level_binary_db:
                    # Convert levelkey to binary and search
                    return Recognition.Result._try_fuzzy_binary_match(levelkey, level_binary_db)
            
            return None
        
        @staticmethod
        def _try_fuzzy_binary_match(hex_key, binary_db, max_distance=20):
            '''Fuzzy binary match for simple hex keys'''
            import numpy as np
            
            # Convert query hex to binary
            query_binary = []
            for hex_char in hex_key:
                if hex_char in '0123456789abcdef':
                    decimal_val = int(hex_char, 16)
                    bits = [(decimal_val >> i) & 1 for i in range(3, -1, -1)]
                    query_binary.extend(bits)
            
            if not query_binary:
                return None
                
            query_array = np.array(query_binary, dtype=np.uint8)
            
            best_match = None
            min_distance = float('inf')
            
            for db_key, entry in binary_db.items():
                db_binary = entry['binary_key']
                
                if len(query_array) == len(db_binary):
                    distance = int(np.sum(query_array != db_binary))
                    if distance <= max_distance and distance < min_distance:
                        min_distance = distance
                        best_match = entry
            
            return best_match['value'] if best_match else None
        
        @staticmethod
        def _save_failed_difficulty_recognition(np_value_informations):
            '''Save failed difficulty recognition image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            
            try:
                debug_dir = os.path.join('failed_results', 'difficulty')
                os.makedirs(debug_dir, exist_ok=True)
                
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                if resource.informations and 'difficulty' in resource.informations:
                    trimmed = np_value_informations[resource.informations['difficulty']['trim']]
                    img = Image.fromarray(trimmed.astype('uint8'))
                    img.save(filepath)
                    
            except Exception as e:
                pass

        @staticmethod
        def _try_play_mode_fuzzy_recognition(np_value_informations):
            '''Fuzzy recognition for Result play_mode'''
            if resource.informations is None:
                return None
                
            import numpy as np
            
            trimmed = np_value_informations[resource.informations['play_mode']['trim']].flatten()
            maskvalue = resource.informations['play_mode']['maskvalue']
            
            # Try with tolerance for mask value matching
            for tolerance in [1, 2, 5, 10, 15]:
                bins = np.where(np.abs(trimmed - maskvalue) <= tolerance, 1, 0)
                hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs])
                
                if tablekey in resource.informations['play_mode']['table']:
                    return resource.informations['play_mode']['table'][tablekey]
            
            # Try fuzzy binary matching if available
            if 'binary' in resource.informations.get('play_mode', {}):
                binary_db = resource.informations['play_mode']['binary']
                
                # Use original exact binary pattern
                bins = np.where(trimmed==maskvalue, 1, 0)
                hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                original_tablekey = ''.join([format(v, '0x') for v in hexs])
                
                result = Recognition.Result._try_fuzzy_binary_match(original_tablekey, binary_db, max_distance=30)
                if result:
                    return result
            
            return None
        
        @staticmethod
        def _save_failed_play_mode_recognition(np_value_informations):
            '''Save failed play_mode recognition image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            
            try:
                debug_dir = os.path.join('failed_results', 'play_mode')
                os.makedirs(debug_dir, exist_ok=True)
                
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                if resource.informations and 'play_mode' in resource.informations:
                    trimmed = np_value_informations[resource.informations['play_mode']['trim']]
                    img = Image.fromarray(trimmed.astype('uint8'))
                    img.save(filepath)
                    
            except Exception as e:
                pass

        @staticmethod
        def _try_notes_digit_fuzzy_recognition(trimmed_once, digit_pos):
            '''Fuzzy recognition for a single notes digit'''
            if resource.informations is None:
                return None
                
            import numpy as np
            
            maskvalue = resource.informations['notes']['maskvalue']
            
            # Try with tolerance for mask value matching
            for tolerance in [1, 2, 5, 10, 15]:
                bins = np.where(np.abs(trimmed_once - maskvalue) <= tolerance, 1, 0).flatten()
                hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs])
                
                if tablekey in resource.informations['notes']['table']:
                    return resource.informations['notes']['table'][tablekey]
            
            # Try fuzzy binary matching if available
            if 'binary' in resource.informations.get('notes', {}):
                binary_db = resource.informations['notes']['binary']
                
                # Use original exact binary pattern
                bins = np.where(trimmed_once==maskvalue, 1, 0).flatten()
                hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
                original_tablekey = ''.join([format(v, '0x') for v in hexs])
                
                result = Recognition.Result._try_fuzzy_binary_match(original_tablekey, binary_db, max_distance=25)
                if result:
                    return result
            
            return None
        
        @staticmethod
        def _save_failed_notes_recognition(np_value_informations):
            '''Save failed notes recognition image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            
            try:
                debug_dir = os.path.join('failed_results', 'notes')
                os.makedirs(debug_dir, exist_ok=True)
                
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                if resource.informations and 'notes' in resource.informations:
                    trimmed = np_value_informations[resource.informations['notes']['trim']]
                    img = Image.fromarray(trimmed.astype('uint8'))
                    img.save(filepath)
                    
            except Exception as e:
                pass

        @staticmethod
        def _try_play_side_fuzzy_recognition(np_value):
            '''Fuzzy recognition for Result play_side'''
            import numpy as np
            
            for target in define.value_list['play_sides']:
                trimmed = np_value[define.areas_np['play_side'][target]]
                
                # Try with tolerance for pixel matching
                for tolerance in [1, 2, 5, 10]:
                    # Check if pattern matches with tolerance
                    mask = (resource.play_side == 0)
                    diff = np.abs(trimmed.astype(np.int16) - resource.play_side.astype(np.int16))
                    matches_with_tolerance = mask | (diff <= tolerance)
                    
                    if np.all(matches_with_tolerance):
                        return target
            
            return None
        
        @staticmethod
        def _try_has_dead_fuzzy_recognition(np_value, play_side):
            '''Fuzzy recognition for Result has_dead'''
            import numpy as np
            
            trimmed = np_value[define.areas_np['dead'][play_side]]
            
            # Try with tolerance for pixel matching
            for tolerance in [1, 2, 5, 10, 15]:
                mask = (resource.dead == 0)
                diff = np.abs(trimmed.astype(np.int16) - resource.dead.astype(np.int16))
                matches_with_tolerance = mask | (diff <= tolerance)
                
                if np.all(matches_with_tolerance):
                    return True
            
            return False
        
        @staticmethod
        def _try_has_rival_fuzzy_recognition(np_value):
            '''Fuzzy recognition for Result has_rival'''
            import numpy as np
            
            trimmed = np_value[define.areas_np['rival']]
            
            # Try with tolerance for pixel matching
            for tolerance in [1, 2, 5, 10, 15]:
                mask = (resource.rival == 0)
                diff = np.abs(trimmed.astype(np.int16) - resource.rival.astype(np.int16))
                matches_with_tolerance = mask | (diff <= tolerance)
                
                if np.all(matches_with_tolerance):
                    return True
            
            return False
        
        @staticmethod
        def _save_failed_play_side_recognition(np_value):
            '''Save failed play_side recognition image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            
            try:
                debug_dir = os.path.join('failed_results', 'play_side')
                os.makedirs(debug_dir, exist_ok=True)
                
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                # Save the relevant play_side areas
                for target in define.value_list['play_sides']:
                    try:
                        trimmed = np_value[define.areas_np['play_side'][target]]
                        target_filename = f'{timestamp}_{target}.png'
                        target_filepath = os.path.join(debug_dir, target_filename)
                        img = Image.fromarray(trimmed.astype('uint8'))
                        img.save(target_filepath)
                    except:
                        continue
                    
            except Exception as e:
                pass

        @staticmethod
        def _try_options_fuzzy_recognition(trimmed, original_tablekey):
            '''Fuzzy recognition for Result options'''
            import numpy as np
            
            if resource.details is None:
                return None
            
            # First extract the relevant portion for key generation
            trimmed_for_key = trimmed[:, :resource.details['option']['lengths'][0]*2]
            
            # Generate binary key with exact mask value first
            maskvalue = resource.details['define']['option']['maskvalue']
            
            # Try with different mask value tolerances and Hamming distances
            for mask_tolerance in [0, 5, 10, 15, 20]:
                # Generate binary pattern based on mask tolerance
                if mask_tolerance > 0:
                    bins = np.where(np.abs(trimmed_for_key[:, ::4].astype(np.int16) - maskvalue) <= mask_tolerance, 1, 0).T
                else:
                    bins = np.where(trimmed_for_key[:, ::4] == maskvalue, 1, 0).T
                
                # Try with progressively larger Hamming distance tolerance
                for max_bit_errors in [0, 1, 2, 3, 5, 8, 10]:
                    # For exact match (0 errors), use traditional method
                    if max_bit_errors == 0:
                        hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                        exact_tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                        
                        for length in resource.details['option']['lengths']:
                            test_key = exact_tablekey[:length]
                            if test_key in resource.details['option']:
                                return resource.details['option'][test_key]
                    else:
                        # Use Hamming distance for fuzzy matching
                        result = Recognition.Result._find_option_with_hamming_distance(
                            bins.flatten(), 
                            resource.details['option'], 
                            resource.details['option']['lengths'],
                            max_bit_errors
                        )
                        if result:
                            return result
            
            # Try fuzzy binary matching for option keys
            if hasattr(resource, 'details_binary') and 'option' in getattr(resource, 'details_binary', {}):
                binary_db = resource.details_binary['option']
                
                # Try different lengths of the original key
                for length in resource.details['option']['lengths']:
                    test_key = original_tablekey[:length]
                    result = Recognition.Result._try_fuzzy_binary_match(test_key, binary_db, max_distance=20)
                    if result:
                        return result
            
            return None
        
        @staticmethod
        def _save_failed_options_recognition(np_value):
            '''Save failed options recognition image for debugging'''
            import os
            from datetime import datetime
            from PIL import Image
            
            try:
                debug_dir = os.path.join('failed_results', 'options')
                os.makedirs(debug_dir, exist_ok=True)
                
                now = datetime.now()
                timestamp = now.strftime('%Y%m%d-%H%M%S-%f')
                filename = f'{timestamp}.png'
                filepath = os.path.join(debug_dir, filename)
                
                # Save options area for both playsides if possible
                if resource.details and 'define' in resource.details and 'option' in resource.details['define']:
                    try:
                        playside = define.details_get_playside(np_value)
                        trimmed = np_value[resource.details['define']['option']['trim'][playside]]
                        img = Image.fromarray(trimmed.astype('uint8'))
                        img.save(filepath)
                    except:
                        pass
                    
            except Exception as e:
                pass

        @staticmethod
        def _find_option_with_hamming_distance(query_bins, option_table, lengths, max_distance):
            '''Find option key using Hamming distance matching'''
            import numpy as np
            
            query_bins = np.array(query_bins)
            best_match = None
            best_distance = float('inf')
            
            # Convert query binary to hex string for comparison
            hexs = query_bins[::4]*8+query_bins[1::4]*4+query_bins[2::4]*2+query_bins[3::4]
            query_hex_full = ''.join([format(int(v), '0x') for v in hexs])
            
            # Try each possible length
            for length in lengths:
                query_hex = query_hex_full[:length]
                query_bits_for_length = query_bins[:length*4]  # 4 bits per hex char
                
                # Check each option key
                for option_key, option_value in option_table.items():
                    # Skip non-hex keys
                    if option_key in ['lengths', 'width']:
                        continue
                    
                    # Only compare keys of the same length
                    if len(option_key) != length:
                        continue
                    
                    # Convert option key to binary
                    option_bits = []
                    for hex_char in option_key:
                        if hex_char in '0123456789abcdef':
                            val = int(hex_char, 16)
                            bits = [(val >> i) & 1 for i in range(3, -1, -1)]
                            option_bits.extend(bits)
                    
                    if len(option_bits) != len(query_bits_for_length):
                        continue
                    
                    # Calculate Hamming distance
                    option_bits = np.array(option_bits)
                    distance = np.sum(query_bits_for_length != option_bits)
                    
                    # Check if this is a better match
                    if distance <= max_distance and distance < best_distance:
                        best_distance = distance
                        best_match = option_value
            
            return best_match

        @staticmethod
        def _try_digit_fuzzy_recognition(trimmed_digit, maskvalue, digit_table):
            '''Fuzzy recognition for individual digits using Hamming distance'''
            import numpy as np
            
            # Try with mask value tolerance first
            for mask_tolerance in [0, 3, 5, 8, 10, 15]:
                if mask_tolerance > 0:
                    bins = np.where(np.abs(trimmed_digit.astype(np.int16) - maskvalue) <= mask_tolerance, 1, 0).T
                else:
                    bins = np.where(trimmed_digit == maskvalue, 1, 0).T
                
                # Try with different Hamming distances
                for max_bit_errors in [0, 1, 2, 3, 5]:
                    if max_bit_errors == 0:
                        # Exact match
                        hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                        tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                        if tablekey in digit_table:
                            return digit_table[tablekey]
                    else:
                        # Hamming distance search
                        result = Recognition.Result._find_digit_with_hamming_distance(
                            bins.flatten(), digit_table, max_bit_errors
                        )
                        if result is not None:
                            return result
            
            return None

        @staticmethod
        def _find_digit_with_hamming_distance(query_bins, digit_table, max_distance):
            '''Find digit using Hamming distance'''
            import numpy as np
            
            query_bins = np.array(query_bins)
            best_match = None
            best_distance = float('inf')
            
            for table_key, digit_value in digit_table.items():
                # Convert table key to binary
                table_bits = []
                for hex_char in table_key:
                    if hex_char in '0123456789abcdef':
                        val = int(hex_char, 16)
                        bits = [(val >> i) & 1 for i in range(3, -1, -1)]
                        table_bits.extend(bits)
                
                if len(table_bits) != len(query_bins):
                    continue
                
                table_bits = np.array(table_bits)
                distance = np.sum(query_bins != table_bits)
                
                if distance <= max_distance and distance < best_distance:
                    best_distance = distance
                    best_match = digit_value
            
            return best_match

        @staticmethod
        def _try_graphtype_fuzzy_recognition(np_value):
            '''Fuzzy recognition for Result graphtype'''
            import numpy as np
            
            if resource.details is None:
                return None
            
            playside = define.details_get_playside(np_value)
            
            # Try with tolerance for pixel matching
            for key, value in resource.details['graphtype'].items():
                trimmed = np_value[resource.details['define']['graphtype'][playside][key]]
                
                # Try with tolerance
                for tolerance in [1, 2, 5, 10]:
                    diff = np.abs(trimmed.astype(np.int16) - value.astype(np.int16))
                    matches_with_tolerance = diff <= tolerance
                    
                    if np.all(matches_with_tolerance):
                        return key
            
            return None

        @staticmethod
        def get_options(np_value):
            if resource.details is None:
                return None

            playside = define.details_get_playside(np_value)
            trimmed = np_value[resource.details['define']['option']['trim'][playside]]

            def generatekey(np_value):
                bins = np.where(np_value[:, ::4]==resource.details['define']['option']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                return ''.join([format(v, '0x') for v in hexs.flatten()])

            arrange = None
            flip = None
            assist = None
            battle = False
            while True:
                tablekey = generatekey(trimmed[:, :resource.details['option']['lengths'][0]*2])
                value = None
                for length in resource.details['option']['lengths']:
                    if tablekey[:length] in resource.details['option'].keys():
                        value = resource.details['option'][tablekey[:length]]
                        break
                
                if value is None:
                    # === FUZZY RECOGNITION FOR RESULT OPTIONS (new addition) ===
                    if resource.fuzzy_search_enabled:
                        fuzzy_value = Recognition.Result._try_options_fuzzy_recognition(trimmed, tablekey)
                        if fuzzy_value:
                            value = fuzzy_value
                        else:
                            break
                    else:
                        break

                arrange_dp_left = False
                if value in define.value_list['options_arrange']:
                    arrange = value
                if value in define.value_list['options_arrange_dp']:
                    if arrange is None:
                        arrange = f'{value}/'
                        arrange_dp_left = True
                    else:
                        arrange += value
                if value in define.value_list['options_arrange_sync']:
                    arrange = value
                if value in define.value_list['options_flip']:
                    flip = value
                if value in define.value_list['options_assist']:
                    assist = value
                if value == 'BATTLE':
                    battle = True
                if not arrange_dp_left:
                    trimmed = trimmed[:, resource.details['define']['option']['width'][value] + resource.details['define']['option']['width'][',']:]
                else:
                    trimmed = trimmed[:, resource.details['define']['option']['width'][value] + resource.details['define']['option']['width']['/']:]
            
            # Save failed options recognition if nothing was found
            if resource.fuzzy_search_enabled and arrange is None and flip is None and assist is None and not battle:
                Recognition.Result._save_failed_options_recognition(np_value)
            
            return ResultOptions(arrange, flip, assist, battle)

        @staticmethod
        def get_graphtype(np_value):
            if resource.details is None:
                return None

            for key, value in resource.details['graphtype'].items():
                playside = define.details_get_playside(np_value)
                trimmed = np_value[resource.details['define']['graphtype'][playside][key]]
                if np.all(trimmed==value):
                    return key
            
            # === FUZZY RECOGNITION FOR RESULT GRAPHTYPE (new addition) ===
            if resource.fuzzy_search_enabled:
                result = Recognition.Result._try_graphtype_fuzzy_recognition(np_value)
                if result:
                    return result
            
            return 'gauge'

        @staticmethod
        def get_clear_type(np_value):
            if resource.details is None:
                return None

            result = {'best': None, 'current': None}
            for key in result.keys():
                trimmed = np_value[resource.details['define']['clear_type'][key]]
                uniques, counts = np.unique(trimmed, return_counts=True)
                color = uniques[np.argmax(counts)]
                if color in resource.details['clear_type'].keys():
                    result[key] = resource.details['clear_type'][color]
            
            trimmed = np_value[resource.details['define']['clear_type']['new']]
            if np.all((resource.details['not_new']==0)|(trimmed==resource.details['not_new'])):
                isnew = False
            else:
                isnew = True
            
            return ResultValues(result['best'], result['current'], isnew)

        @staticmethod
        def get_dj_level(np_value):
            if resource.details is None:
                return None

            result = {'best': None, 'current': None}
            for key in result.keys():
                trimmed = np_value[resource.details['define']['dj_level'][key]]
                count = np.count_nonzero(trimmed==resource.details['define']['dj_level']['maskvalue'])
                if count in resource.details['dj_level'].keys():
                    result[key] = resource.details['dj_level'][count]
            
            trimmed = np_value[resource.details['define']['dj_level']['new']]
            if np.all((resource.details['not_new']==0)|(trimmed==resource.details['not_new'])):
                isnew = False
            else:
                isnew = True
            
            return ResultValues(result['best'], result['current'], isnew)

        @staticmethod
        def get_score(np_value):
            if resource.details is None:
                return None

            trimmed = np_value[resource.details['define']['score']['best']]
            best = None
            for dig in range(resource.details['define']['score']['digit']):
                splitted = np.hsplit(trimmed, resource.details['define']['score']['digit'])
                trimmed_once = splitted[-(dig+1)][resource.details['define']['numberbest']['trim']]
                bins = np.where(trimmed_once==resource.details['define']['numberbest']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if not tablekey in resource.details['number_best'].keys():
                    # === FUZZY RECOGNITION FOR SCORE BEST DIGITS (new addition) ===
                    if resource.fuzzy_search_enabled:
                        fuzzy_digit = Recognition.Result._try_digit_fuzzy_recognition(
                            trimmed_once, 
                            resource.details['define']['numberbest']['maskvalue'],
                            resource.details['number_best']
                        )
                        if fuzzy_digit is not None:
                            if best is None:
                                best = 0
                            best += 10 ** dig * fuzzy_digit
                            continue
                    break
                if best is None:
                    best = 0
                best += 10 ** dig * resource.details['number_best'][tablekey]

            trimmed = np_value[resource.details['define']['score']['current']]
            current = None
            for dig in range(resource.details['define']['score']['digit']):
                splitted = np.hsplit(trimmed, resource.details['define']['score']['digit'])
                trimmed_once = splitted[-(dig+1)][resource.details['define']['numbercurrent']['trim']]
                bins = np.where(trimmed_once==resource.details['define']['numbercurrent']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if not tablekey in resource.details['number_current'].keys():
                    # === FUZZY RECOGNITION FOR SCORE CURRENT DIGITS (new addition) ===
                    if resource.fuzzy_search_enabled:
                        fuzzy_digit = Recognition.Result._try_digit_fuzzy_recognition(
                            trimmed_once, 
                            resource.details['define']['numbercurrent']['maskvalue'],
                            resource.details['number_current']
                        )
                        if fuzzy_digit is not None:
                            if current is None:
                                current = 0
                            current += 10 ** dig * fuzzy_digit
                            continue
                    break
                if current is None:
                    current = 0
                current += 10 ** dig * resource.details['number_current'][tablekey]
            
            trimmed = np_value[resource.details['define']['score']['new']]
            if np.all((resource.details['not_new']==0)|(trimmed==resource.details['not_new'])):
                isnew = False
            else:
                isnew = True
            
            return ResultValues(best, current, isnew)

        @staticmethod
        def get_miss_count(np_value):
            if resource.details is None:
                return None

            trimmed = np_value[resource.details['define']['miss_count']['best']]
            best = None
            for dig in range(resource.details['define']['miss_count']['digit']):
                splitted = np.hsplit(trimmed, resource.details['define']['miss_count']['digit'])
                trimmed_once = splitted[-(dig+1)][resource.details['define']['numberbest']['trim']]
                bins = np.where(trimmed_once==resource.details['define']['numberbest']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if not tablekey in resource.details['number_best'].keys():
                    # === FUZZY RECOGNITION FOR MISS_COUNT BEST DIGITS (new addition) ===
                    if resource.fuzzy_search_enabled:
                        fuzzy_digit = Recognition.Result._try_digit_fuzzy_recognition(
                            trimmed_once, 
                            resource.details['define']['numberbest']['maskvalue'],
                            resource.details['number_best']
                        )
                        if fuzzy_digit is not None:
                            if best is None:
                                best = 0
                            best += 10 ** dig * fuzzy_digit
                            continue
                    break
                if best is None:
                    best = 0
                best += 10 ** dig * resource.details['number_best'][tablekey]

            trimmed = np_value[resource.details['define']['miss_count']['current']]
            current = None
            for dig in range(resource.details['define']['miss_count']['digit']):
                splitted = np.hsplit(trimmed, resource.details['define']['miss_count']['digit'])
                trimmed_once = splitted[-(dig+1)][resource.details['define']['numbercurrent']['trim']]
                bins = np.where(trimmed_once==resource.details['define']['numbercurrent']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if not tablekey in resource.details['number_current'].keys():
                    # === FUZZY RECOGNITION FOR MISS_COUNT CURRENT DIGITS (new addition) ===
                    if resource.fuzzy_search_enabled:
                        fuzzy_digit = Recognition.Result._try_digit_fuzzy_recognition(
                            trimmed_once, 
                            resource.details['define']['numbercurrent']['maskvalue'],
                            resource.details['number_current']
                        )
                        if fuzzy_digit is not None:
                            if current is None:
                                current = 0
                            current += 10 ** dig * fuzzy_digit
                            continue
                    break
                if current is None:
                    current = 0
                current += 10 ** dig * resource.details['number_current'][tablekey]
            
            trimmed = np_value[resource.details['define']['miss_count']['new']]
            if np.all((resource.details['not_new']==0)|(trimmed==resource.details['not_new'])):
                isnew = False
            else:
                isnew = True
            
            return ResultValues(best, current, isnew)
        
        @staticmethod
        def get_graphtarget(np_value):
            if resource.details is None:
                return None

            trimmed = np_value[resource.details['define']['graphtarget']['trimmode']]
            uniques, counts = np.unique(trimmed, return_counts=True)
            mode = uniques[np.argmax(counts)]
            if not mode in resource.details['graphtarget'].keys():
                return None
            
            trimmed = np_value[resource.details['define']['graphtarget']['trimkey']]
            bins = np.where(trimmed==mode, 1, 0)
            hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
            tablekey = ''.join([format(v, '0x') for v in hexs])
            if not tablekey in resource.details['graphtarget'][mode].keys():
                return None
            
            return resource.details['graphtarget'][mode][tablekey]

        @classmethod
        def get_informations(cls, np_value):
            play_mode = cls.get_play_mode(np_value)
            difficulty, level = cls.get_difficulty(np_value)
            notes = cls.get_notes(np_value)
            music = cls.get_music(np_value)

            return ResultInformations(play_mode, difficulty, level, notes, music)

        @classmethod
        def get_details(cls, np_value):
            graphtype = cls.get_graphtype(np_value)
            if graphtype == 'gauge':
                options = cls.get_options(np_value)
            else:
                options = None

            clear_type = cls.get_clear_type(np_value)
            dj_level = cls.get_dj_level(np_value)
            score = cls.get_score(np_value)
            miss_count = cls.get_miss_count(np_value)
            graphtarget = cls.get_graphtarget(np_value)

            return ResultDetails(graphtype, options, clear_type, dj_level, score, miss_count, graphtarget)

    class MusicSelect():
        @staticmethod
        def get_playmode(np_value):
            if resource.musicselect is None:
                return None
            if not 'playmode' in resource.musicselect.keys():
                return None
            trimmed = np_value[resource.musicselect['playmode']['trim']].flatten()
            bins = np.where(trimmed==resource.musicselect['playmode']['maskvalue'], 1, 0)
            hexs=bins[::4]*8+bins[1::4]*4+bins[2::4]*2+bins[3::4]
            tablekey = ''.join([format(v, '0x') for v in hexs])
            if not tablekey in resource.musicselect['playmode']['table'].keys():
                return None
            return resource.musicselect['playmode']['table'][tablekey]
        
        @staticmethod
        def get_version(np_value):
            if resource.musicselect is None:
                return None
            
            # Check if fuzzy search is enabled for tolerance
            use_tolerance = resource.fuzzy_search_enabled
            
            for table in resource.musicselect['version']:
                cropped = np_value[table['trim']]
                reshaped = cropped.reshape(cropped.shape[0]*cropped.shape[1], cropped.shape[2])
                hexes = [''.join([format(b, '02x') for b in point]) for point in reshaped]
                tablekey = ''.join(hexes)

                # Try exact match first
                if tablekey in table['table'].keys():
                    return table['table'][tablekey]
                
                # If fuzzy search enabled, try tolerance-based matching
                if use_tolerance:
                    # Convert hex string to numpy array for comparison
                    query_bytes = bytes.fromhex(tablekey)
                    query_array = np.frombuffer(query_bytes, dtype=np.uint8)
                    
                    # Try fuzzy matching against all table keys
                    for stored_key in table['table'].keys():
                        try:
                            stored_bytes = bytes.fromhex(stored_key)
                            stored_array = np.frombuffer(stored_bytes, dtype=np.uint8)
                            
                            # Calculate color difference tolerance
                            if len(query_array) == len(stored_array):
                                # Allow small color value differences (tolerance of 10 per channel)
                                diff = np.abs(query_array.astype(np.int16) - stored_array.astype(np.int16))
                                if np.all(diff <= 10):
                                    return table['table'][stored_key]
                        except (ValueError, TypeError):
                            continue
                            
            return None

        @staticmethod
        def get_musicname(np_value):
            if resource.musicselect is None:
                return None
            
            # === EXACT MATCHING (original master branch logic) ===
            
            # 1. infinitas exact matching
            resource_target = resource.musicselect['musicname']['infinitas']
            cropped = np_value[resource_target['trim']]
            filtereds = []
            for index in range(len(resource_target['thresholds'])):
                threshold = resource_target['thresholds'][index]
                masked = np.where((threshold[0]<=cropped[:,:,index])&(cropped[:,:,index]<=threshold[1]), 1, 0)
                filtereds.append(masked)
            bins = np.where((filtereds[0]==1)&(filtereds[1]==1)&(filtereds[2]==1), 1, 0)
            hexes = [line[::4]*8+line[1::4]*4+line[2::4]*2+line[3::4] for line in bins]
            recogkeys = [''.join([format(v, '0x') for v in line]) for line in hexes]
            tabletarget = resource_target['table']
            for recogkey in recogkeys:
                if not recogkey in tabletarget.keys():
                    break
                if type(tabletarget[recogkey]) is str:
                    return tabletarget[recogkey]
                tabletarget = tabletarget[recogkey]
            
            # 2. leggendaria exact matching
            resource_target = resource.musicselect['musicname']['leggendaria']
            cropped = np_value[resource_target['trim']]
            filtereds = []
            for index in range(len(resource_target['thresholds'])):
                threshold = resource_target['thresholds'][index]
                masked = np.where((threshold[0]<=cropped[:,:,index])&(cropped[:,:,index]<=threshold[1]), 1, 0)
                filtereds.append(masked)
            bins = np.where((filtereds[0]==1)&(filtereds[1]==1)&(filtereds[2]==1), 1, 0)
            hexes = [line[::4]*8+line[1::4]*4+line[2::4]*2+line[3::4] for line in bins]
            recogkeys = [''.join([format(v, '0x') for v in line]) for line in hexes]
            tabletarget = resource_target['table']
            for recogkey in recogkeys:
                if not recogkey in tabletarget.keys():
                    break
                if type(tabletarget[recogkey]) is str:
                    return tabletarget[recogkey]
                tabletarget = tabletarget[recogkey]

            # 3. arcade exact matching
            resource_target = resource.musicselect['musicname']['arcade']
            thresholds = resource_target['thresholds']
            cropped = np_value[resource_target['trim']]
            masked = np.where((cropped[:,:,0]==cropped[:,:,1])&(cropped[:,:,0]==cropped[:,:,2]),cropped[:,:,0], 0)
            bins = [np.where((thresholds[i][0]<=masked[i])&(masked[i]<=thresholds[i][1]), 1, 0) for i in range(masked.shape[0])]
            shrunk = [line[::2]&line[1::2] for line in bins]
            hexes = [line[::4]*8+line[1::4]*4+line[2::4]*2+line[3::4] for line in shrunk]
            recogkeys = [''.join([format(v, '0x') for v in line]) for line in hexes]
            tabletarget = resource_target['table']
            for recogkey in recogkeys:
                if not recogkey in tabletarget.keys():
                    break
                if type(tabletarget[recogkey]) is str:
                    return tabletarget[recogkey]
                tabletarget = tabletarget[recogkey]
            
            # === FUZZY MATCHING (new addition) ===
            if resource.fuzzy_search_enabled:
                categories = ['infinitas', 'leggendaria', 'arcade']
                for category in categories:
                    fuzzy_result = Recognition.MusicSelect._try_fuzzy_recognition_category(np_value, category)
                    if fuzzy_result:
                        return fuzzy_result
            
            return None
        
        
        @staticmethod
        def _try_fuzzy_recognition_category(np_value, category):
            """Try fuzzy recognition for specified category using unified strategy system"""
            import time
            import numpy as np
            import json
            
            # Check if fuzzy search is enabled and database exists
            binary_key = f'{category}_binary'
            if (not hasattr(resource.musicselect, 'get') or 
                not resource.musicselect.get('musicname', {}).get(binary_key)):
                return None
            
            try:
                start_time = time.time()
                
                # Get pre-built binary database
                binary_db = resource.musicselect['musicname'][binary_key]
                category_config = resource.musicselect['musicname'][category]
                
                # Log performance start
                log_entry = {
                    "timestamp": int(start_time * 1000),
                    "phase": f"{category}_fuzzy_recognition",
                    "success": False,
                    "result": None,
                    "total_time_ms": 0,
                    "strategies_tried": []
                }
                
                # Try strategies in order of effectiveness (shared across all categories)
                tolerance_strategies = [
                    (0, 0),   # Most effective - exact match first
                    (0, 1), (0, 2), (0, 6), (1, 4), (0, 7),
                    (2, 0), (1, 3), (3, 0), (4, 0), (1, 1), 
                    (5, 1), (2, 2), (0, 5)
                ]
                
                for gray_tolerance, threshold_tolerance in tolerance_strategies:
                    strategy_start = time.time()
                    
                    result, distance = Recognition.MusicSelect._try_fuzzy_strategy(
                        np_value, gray_tolerance, threshold_tolerance, 
                        binary_db, category_config, category
                    )
                    
                    strategy_time = (time.time() - strategy_start) * 1000
                    
                    # Log strategy attempt
                    strategy_log = {
                        "gray_tolerance": gray_tolerance,
                        "threshold_tolerance": threshold_tolerance,
                        "time_ms": strategy_time,
                        "success": result is not None,
                        "result": result,
                        "distance": distance if result else None
                    }
                    log_entry["strategies_tried"].append(strategy_log)
                    
                    if result is not None:
                        log_entry["success"] = True
                        log_entry["result"] = result
                        log_entry["winning_distance"] = distance
                        break
                
                # Write performance log
                log_entry["total_time_ms"] = (time.time() - start_time) * 1000
                Recognition.MusicSelect._write_fuzzy_performance_log(log_entry)
                
                return log_entry.get("result")
                
            except Exception as e:
                return None
        
        @staticmethod
        def _try_fuzzy_strategy(np_value, gray_tolerance, threshold_tolerance, binary_db, category_config, category):
            """Try fuzzy recognition with specific tolerance values for any category - DRY unified logic"""
            import numpy as np
            
            # Step 1: Category-specific preprocessing
            category_trim = category_config['trim']
            cropped = np_value[category_trim]
            
            if category == 'arcade':
                # Arcade pipeline: gray filtering → threshold → shrinking
                r, g, b = cropped[:,:,0], cropped[:,:,1], cropped[:,:,2]
                is_gray = (np.abs(r - g) <= gray_tolerance) & (np.abs(r - b) <= gray_tolerance) & (np.abs(g - b) <= gray_tolerance)
                masked = np.where(is_gray, r, 0)
                
                gray_pixel_count = np.count_nonzero(is_gray)
                if gray_pixel_count == 0:
                    return None, None
                
                # Apply threshold filtering
                thresholds = category_config['thresholds']
                bins = []
                for i in range(masked.shape[0]):
                    th_min = max(0, thresholds[i][0] - threshold_tolerance)
                    th_max = min(255, thresholds[i][1] + threshold_tolerance)
                    bin_row = np.where((th_min <= masked[i]) & (masked[i] <= th_max), 1, 0)
                    bins.append(bin_row)
                
                bin_counts = [np.sum(bin_row) for bin_row in bins]
                non_zero_bins = sum(1 for count in bin_counts if count > 0)
                
                if non_zero_bins < 3:
                    return None, None
                
                # Shrinking step (consistent with original logic)
                bins = [line[::2] & line[1::2] for line in bins]
                
            else:
                # Infinitas/Leggendaria pipeline: RGB threshold filtering
                thresholds = category_config['thresholds']
                filtereds = []
                for index in range(len(thresholds)):
                    threshold = thresholds[index]
                    min_threshold = max(0, threshold[0] - threshold_tolerance)
                    max_threshold = min(255, threshold[1] + threshold_tolerance)
                    masked_channel = np.where(
                        (min_threshold <= cropped[:,:,index]) & (cropped[:,:,index] <= max_threshold), 
                        1, 0
                    )
                    filtereds.append(masked_channel)
                
                # Combine all channels
                bins = np.where((filtereds[0]==1) & (filtereds[1]==1) & (filtereds[2]==1), 1, 0)
                
                if np.count_nonzero(bins) == 0:
                    return None, None
            
            # Step 2: Convert to binary path for fuzzy matching (unified for all categories)
            query_binary_path = []
            for line in bins:
                # Process line in 4-bit chunks to match binary database structure (original logic)
                binary_chunks = []
                for i in range(0, len(line), 4):
                    chunk = line[i:i+4]
                    # Pad if necessary
                    while len(chunk) < 4:
                        chunk = np.append(chunk, 0)
                    binary_chunks.extend(chunk)
                query_binary_path.append(np.array(binary_chunks, dtype=np.uint8))
            
            # Step 3: Fuzzy search in pre-built database
            matches = Recognition.MusicSelect._fuzzy_search_direct(query_binary_path, binary_db)
            
            if matches:
                best_match = matches[0]
                return best_match['song_name'], best_match['total_distance']
            
            return None, None
        
        @staticmethod
        def _try_fuzzy_recognition(np_value):
            """Legacy wrapper for arcade-specific fuzzy recognition"""
            return Recognition.MusicSelect._try_fuzzy_recognition_category(np_value, 'arcade')
        
        @staticmethod
        def _fuzzy_search_direct(query_path, binary_db):
            """Direct fuzzy search using pre-built binary database"""
            import numpy as np
            
            matches = []
            max_distance = 50
            
            for db_key, db_entry in binary_db.items():
                db_path = db_entry['binary_path']
                
                # Check path length
                if len(query_path) != len(db_path):
                    continue
                
                # Calculate Hamming distance
                total_distance = 0
                step_distances = []
                
                for query_step, db_step in zip(query_path, db_path):
                    if len(query_step) != len(db_step):
                        total_distance = float('inf')
                        break
                    
                    step_distance = int(np.sum(query_step != db_step))
                    step_distances.append(step_distance)
                    total_distance += step_distance
                    
                    # Early termination
                    if total_distance > max_distance:
                        break
                else:
                    # All steps completed within threshold
                    if total_distance <= max_distance:
                        matches.append({
                            'song_name': db_entry['song_name'],
                            'total_distance': total_distance,
                            'step_distances': step_distances
                        })
            
            # Sort by distance
            matches.sort(key=lambda x: x['total_distance'])
            return matches
        
        @staticmethod
        def _write_fuzzy_performance_log(log_entry):
            """Write fuzzy performance log"""
            import json
            import os
            import time
            
            try:
                cache_dir = os.path.expanduser('~/.cache/inf-notebook')
                os.makedirs(cache_dir, exist_ok=True)
                session_id = int(time.time() * 1000)
                log_path = os.path.join(cache_dir, f'direct_fuzzy_performance_{session_id}.jsonl')
                
                with open(log_path, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception:
                pass
        
        @staticmethod
        def get_difficulty(np_value):
            if resource.musicselect is None:
                return None
            targetresource = resource.musicselect['levels']['select']
            for difficulty in targetresource.keys():
                trimmed = np_value[targetresource[difficulty]['trim']]
                filtereds = []
                for index in range(len(targetresource[difficulty]['thresholds'])):
                    threshold = targetresource[difficulty]['thresholds'][index]
                    masked = np.where((threshold[0]<=trimmed[:,:,index])&(trimmed[:,:,index]<=threshold[1]), 1, 0)
                    filtereds.append(masked)
                bins = np.where((filtereds[0]==1)&(filtereds[1]==1)&(filtereds[2]==1), 1, 0)
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if tablekey in targetresource[difficulty]['table'].keys():
                    return str.upper(difficulty)
            return None

        @staticmethod
        def get_cleartype(np_value):
            if resource.musicselect is None:
                return None
            trimmed = np_value[resource.musicselect['cleartype']['trim']]
            uniques, counts = np.unique(trimmed, return_counts=True)
            if len(uniques) == 0:
                return None
            color = uniques[np.argmax(counts)]
            if color in resource.musicselect['cleartype']['table'].keys():
                return resource.musicselect['cleartype']['table'][color]
            return None

        @staticmethod
        def get_djlevel(np_value):
            if resource.musicselect is None:
                return None
            trimmed = np_value[resource.musicselect['djlevel']['trim']]
            count = np.count_nonzero(trimmed==resource.musicselect['djlevel']['maskvalue'])
            if count in resource.musicselect['djlevel']['table'].keys():
                return resource.musicselect['djlevel']['table'][count]
            return None

        @staticmethod
        def get_score(np_value):
            if resource.musicselect is None:
                return None
            trimmed = np_value[resource.musicselect['score']['trim']]
            score = None
            for dig in range(resource.musicselect['score']['digit']):
                splitted = np.hsplit(trimmed, resource.musicselect['score']['digit'])
                trimmed_once = splitted[-(dig+1)][resource.musicselect['number']['trim']]
                bins = np.where(trimmed_once==resource.musicselect['number']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if not tablekey in resource.musicselect['number']['table'].keys():
                    break
                if score is None:
                    score = 0
                score += 10 ** dig * resource.musicselect['number']['table'][tablekey]
            
            return score

        @staticmethod
        def get_misscount(np_value):
            if resource.musicselect is None:
                return None
            trimmed = np_value[resource.musicselect['misscount']['trim']]
            score = None
            for dig in range(resource.musicselect['misscount']['digit']):
                splitted = np.hsplit(trimmed, resource.musicselect['misscount']['digit'])
                trimmed_once = splitted[-(dig+1)][resource.musicselect['number']['trim']]
                bins = np.where(trimmed_once==resource.musicselect['number']['maskvalue'], 1, 0).T
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if not tablekey in resource.musicselect['number']['table'].keys():
                    break
                if score is None:
                    score = 0
                score += 10 ** dig * resource.musicselect['number']['table'][tablekey]
            
            return score

        @staticmethod
        def get_levels(np_value):
            if resource.musicselect is None:
                return None
            
            ret = {}
            for difficulty in resource.musicselect['levels']['select']:
                resourcetarget = resource.musicselect['levels']['select'][difficulty]
                trimmed = np_value[resourcetarget['trim']]
                
                filtereds = []
                for index in range(len(resourcetarget['thresholds'])):
                    threshold = resourcetarget['thresholds'][index]
                    masked = np.where((threshold[0]<=trimmed[:,:,index])&(trimmed[:,:,index]<=threshold[1]), 1, 0)
                    filtereds.append(masked)
                bins = np.where((filtereds[0]==1)&(filtereds[1]==1)&(filtereds[2]==1), 1, 0)
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if tablekey in resourcetarget['table'].keys():
                    ret[str.upper(difficulty)] = resourcetarget['table'][tablekey]
                    break
            for difficulty in resource.musicselect['levels']['noselect']:
                resourcetarget = resource.musicselect['levels']['noselect'][difficulty]
                trimmed = np_value[resourcetarget['trim']]
                threshold = resourcetarget['threshold']
                filtereds = []
                for index in range(trimmed.shape[2]):
                    masked = np.where((threshold[0]<=trimmed[:,:,index])&(trimmed[:,:,index]<=threshold[1]), 1, 0)
                    filtereds.append(masked)
                bins = np.where((filtereds[0]==1)&(filtereds[1]==1)&(filtereds[2]==1), 1, 0)
                hexs = bins[:,0::4]*8+bins[:,1::4]*4+bins[:,2::4]*2+bins[:,3::4]
                tablekey = ''.join([format(v, '0x') for v in hexs.flatten()])
                if tablekey in resourcetarget['table'].keys():
                    ret[str.upper(difficulty)] = resourcetarget['table'][tablekey]
            return ret

    @staticmethod
    def get_is_savable(np_value):
        define_result_check = define.result_check

        pixel = np_value[resource.is_savable['keyposition']]
        background_key = ''.join([format(v, '02x') for v in pixel])
        if not background_key in resource.is_savable['areas'].keys():
            return False

        for area_key, area in define_result_check.items():
            if not np.array_equal(np_value[area], resource.is_savable['areas'][background_key][area_key]):
                return False
        
        return True
        
    @classmethod
    def get_result(cls, screen):
        play_side = cls.Result.get_play_side(screen.np_value)
        if play_side == None:
            return None

        result = Result(
            cls.Result.get_informations(screen.np_value[define.areas_np['informations']]),
            play_side,
            cls.Result.get_has_rival(screen.np_value),
            cls.Result.get_has_dead(screen.np_value, play_side),
            cls.Result.get_details(screen.np_value[define.areas_np['details'][play_side]])
        )
    
        return result
