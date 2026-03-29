#!/usr/bin/env python3
"""
Concurrent add/remove test for the web crawler app.
Tests that concurrent requests don't cause data loss or corruption.
"""

import threading
import time
import requests
import sys

BASE_URL = 'http://localhost:5000'

def test_concurrent_adds(num_threads=10):
    """Test adding items concurrently."""
    print(f"\n[TEST] Adding {num_threads} items concurrently...")
    
    def add_item(item_name):
        try:
            resp = requests.post(f'{BASE_URL}/add', data={'add_item': item_name}, timeout=5)
            if resp.json()['success']:
                print(f"  ✓ Added: {item_name}")
            else:
                print(f"  ✗ Failed to add: {item_name}")
        except Exception as e:
            print(f"  ✗ Error adding {item_name}: {e}")
    
    threads = []
    for i in range(num_threads):
        item_name = f"test_user_{i}_{int(time.time())}"
        t = threading.Thread(target=add_item, args=(item_name,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print("  [CHECK] Verifying all items were saved...")
    time.sleep(0.5)
    try:
        resp = requests.get(f'{BASE_URL}/', timeout=5)
        # Count items in response (simple text count)
        text = resp.text
        test_items = [f"test_user_{i}" for i in range(num_threads)]
        found_count = sum(1 for item in test_items if item in text for _ in [1])
        print(f"  ✓ Found {found_count}/{num_threads} items in response")
        return found_count == num_threads
    except Exception as e:
        print(f"  ✗ Error verifying: {e}")
        return False

def test_concurrent_mixed(num_threads=5):
    """Test adding and removing items concurrently."""
    print(f"\n[TEST] Concurrent adds and removes ({num_threads} threads each)...")
    
    results = {'added': 0, 'removed': 0, 'errors': 0}
    results_lock = threading.Lock()
    
    def add_item(item_name):
        try:
            resp = requests.post(f'{BASE_URL}/add', data={'add_item': item_name}, timeout=5)
            if resp.json()['success']:
                with results_lock:
                    results['added'] += 1
        except Exception as e:
            with results_lock:
                results['errors'] += 1
    
    def remove_item(item_name):
        time.sleep(0.1)  # Let adds complete first
        try:
            resp = requests.post(f'{BASE_URL}/remove', data={'remove_item': item_name}, timeout=5)
            if resp.json()['success']:
                with results_lock:
                    results['removed'] += 1
        except Exception as e:
            with results_lock:
                results['errors'] += 1
    
    threads = []
    for i in range(num_threads):
        item_name = f"mixed_{i}_{int(time.time())}"
        t1 = threading.Thread(target=add_item, args=(item_name,))
        threads.append(t1)
        t1.start()
    
    for i in range(num_threads):
        item_name = f"mixed_{i}_{int(time.time())}"
        t2 = threading.Thread(target=remove_item, args=(item_name,))
        threads.append(t2)
        t2.start()
    
    for t in threads:
        t.join()
    
    print(f"  ✓ Added: {results['added']}, Removed: {results['removed']}, Errors: {results['errors']}")
    return results['errors'] == 0

def main():
    print("\n" + "="*60)
    print("  WEB CRAWLER CONCURRENCY TEST")
    print("="*60)
    print(f"\nTarget: {BASE_URL}")
    print("Ensure the Flask app is running before starting tests!")
    
    try:
        resp = requests.get(f'{BASE_URL}/', timeout=2)
        print("✓ App is running")
    except Exception as e:
        print(f"✗ App not responding: {e}")
        print("  Start the app with: python app.py")
        sys.exit(1)
    
    # Run tests
    test1_passed = test_concurrent_adds(num_threads=10)
    time.sleep(1)
    test2_passed = test_concurrent_mixed(num_threads=5)
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"Concurrent adds:     {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"Mixed operations:    {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print("="*60 + "\n")
    
    if test1_passed and test2_passed:
        print("✓ All tests passed! Concurrency handling is working correctly.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Check the app logs for details.")
        sys.exit(1)

if __name__ == '__main__':
    main()
