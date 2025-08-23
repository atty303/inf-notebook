#!/usr/bin/env python3
"""Prepare test suite by moving successful recognition images and creating CSV"""

import sys
import os
import shutil
import csv
from collections import defaultdict

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recog import Recognition, resource
from setting import Setting
from PIL import Image
import numpy as np

def main():
    # Load resources
    if resource.informations is None:
        resource.load_resource_informations()
    if not resource.fuzzy_search_enabled:
        setting = Setting()
        resource._build_fuzzy_database(setting)

    debug_dir = 'debug_results/music_input'
    test_dir = 'test_suite/result_music_images'
    
    # Test all debug images and group by recognition result
    results_by_song = defaultdict(list)
    
    print("Testing all debug images...")
    for img_file in sorted(os.listdir(debug_dir)):
        if img_file.endswith('.png'):
            img_path = os.path.join(debug_dir, img_file)
            img = Image.open(img_path)
            np_array = np.array(img)[:, :, ::-1]  # RGB to BGR
            
            result = Recognition.Result.get_music(np_array)
            if result:
                results_by_song[result].append((img_file, img_path))
                print(f'{img_file}: {result}')
    
    # Select one representative image per song
    test_data = []
    counter = 1
    
    for song_name, file_list in results_by_song.items():
        # Take the first (earliest) image for each song
        original_file, original_path = file_list[0]
        
        # Create a clean filename for test suite
        test_filename = f'test_{counter:03d}_{song_name.replace(" ", "_").replace("/", "_")}.png'
        test_path = os.path.join(test_dir, test_filename)
        
        # Copy file to test suite
        shutil.copy2(original_path, test_path)
        test_data.append((test_filename, song_name))
        
        print(f'Moved {original_file} -> {test_filename} (expected: {song_name})')
        counter += 1
    
    # Create CSV file
    csv_path = os.path.join('test_suite', 'result_music_test_data.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['filename', 'expected_song'])
        for filename, song_name in sorted(test_data):
            writer.writerow([filename, song_name])
    
    print(f'\nCreated test suite:')
    print(f'  Images: {len(test_data)} files in {test_dir}')
    print(f'  Data: {csv_path}')
    print(f'  Songs covered: {", ".join(sorted(results_by_song.keys()))}')

if __name__ == "__main__":
    main()