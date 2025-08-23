#!/usr/bin/env python3
"""Test suite for Result music recognition"""

import sys
import os
import csv
import time
from typing import List, Tuple, Dict

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recog import Recognition, resource
from setting import Setting
from PIL import Image
import numpy as np

class TestResult:
    def __init__(self, filename: str, expected: str, actual: str, success: bool, time_ms: float):
        self.filename = filename
        self.expected = expected
        self.actual = actual
        self.success = success
        self.time_ms = time_ms

def load_test_data(csv_path: str) -> List[Tuple[str, str]]:
    """Load test data from CSV file"""
    test_data = []
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            test_data.append((row['filename'], row['expected_song']))
    
    return test_data

def run_recognition_test(image_path: str) -> Tuple[str, float]:
    """Run recognition on a single image and return result with timing"""
    img = Image.open(image_path)
    np_array = np.array(img)[:, :, ::-1]  # RGB to BGR
    
    start_time = time.time()
    result = Recognition.Result.get_music(np_array)
    end_time = time.time()
    
    time_ms = (end_time - start_time) * 1000
    return result, time_ms

def run_test_suite() -> Dict[str, any]:
    """Run the complete test suite"""
    print("🎵 Result Music Recognition Test Suite")
    print("=" * 50)
    
    # Initialize resources
    print("Initializing resources...")
    if resource.informations is None:
        resource.load_resource_informations()
    
    if not resource.fuzzy_search_enabled:
        setting = Setting()
        resource._build_fuzzy_database(setting)
    
    print("✓ Resources loaded\n")
    
    # Load test data
    csv_path = os.path.join('test_suite', 'result_music_test_data.csv')
    test_data = load_test_data(csv_path)
    
    print(f"Loaded {len(test_data)} test cases from {csv_path}\n")
    
    # Run tests
    results = []
    test_dir = os.path.join('test_suite', 'result_music_images')
    
    for filename, expected_song in test_data:
        image_path = os.path.join(test_dir, filename)
        
        if not os.path.exists(image_path):
            print(f"❌ MISSING: {filename}")
            results.append(TestResult(filename, expected_song, "FILE_NOT_FOUND", False, 0.0))
            continue
        
        try:
            actual_result, time_ms = run_recognition_test(image_path)
            success = actual_result == expected_song
            
            if success:
                print(f"✅ PASS: {filename} -> '{actual_result}' ({time_ms:.1f}ms)")
            else:
                print(f"❌ FAIL: {filename}")
                print(f"   Expected: '{expected_song}'")
                print(f"   Actual:   '{actual_result or 'None'}'")
            
            results.append(TestResult(filename, expected_song, actual_result or "None", success, time_ms))
        
        except Exception as e:
            print(f"❌ ERROR: {filename} - {str(e)}")
            results.append(TestResult(filename, expected_song, f"ERROR: {str(e)}", False, 0.0))
    
    # Calculate statistics
    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed
    pass_rate = (passed / len(results)) * 100 if results else 0
    avg_time = sum(r.time_ms for r in results if r.success) / passed if passed > 0 else 0
    
    print(f"\n{'=' * 50}")
    print(f"📊 Test Results Summary")
    print(f"{'=' * 50}")
    print(f"Total tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Pass rate: {pass_rate:.1f}%")
    print(f"⏱️  Average time: {avg_time:.1f}ms")
    
    # Show failed tests
    failed_tests = [r for r in results if not r.success]
    if failed_tests:
        print(f"\n🔍 Failed Tests:")
        for result in failed_tests:
            print(f"   {result.filename}: expected '{result.expected}' got '{result.actual}'")
    
    return {
        'total': len(results),
        'passed': passed,
        'failed': failed,
        'pass_rate': pass_rate,
        'avg_time_ms': avg_time,
        'results': results
    }

def main():
    """Main entry point"""
    try:
        stats = run_test_suite()
        
        # Exit with non-zero code if any tests failed
        if stats['failed'] > 0:
            print(f"\n💥 Test suite failed with {stats['failed']} failures")
            sys.exit(1)
        else:
            print(f"\n🎉 All tests passed!")
            sys.exit(0)
    
    except Exception as e:
        print(f"\n💥 Test suite crashed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()