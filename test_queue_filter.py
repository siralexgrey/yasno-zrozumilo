#!/usr/bin/env python3
"""
Test queue filtering functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import format_schedule
import requests

API_URL = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/3/dsos/301/planned-outages"

def test_queue_filtering():
    """Test the queue filtering feature"""
    print("🧪 Testing Queue Filtering\n")
    print("="*60)
    
    # Fetch data
    print("📥 Fetching data from API...")
    response = requests.get(API_URL, timeout=10)
    data = response.json()
    
    print(f"✅ Got data for {len(data)} queues\n")
    
    # Test 1: Show all queues (no filter)
    print("Test 1: All queues (no filter)")
    print("-" * 60)
    result = format_schedule(data)
    print(f"Length: {len(result)} characters")
    print(f"Contains all queues: {'1.1' in result and '5.1' in result and '6.2' in result}")
    print()
    
    # Test 2: Filter by queue 5.1
    print("Test 2: Filter by queue 5.1")
    print("-" * 60)
    result = format_schedule(data, "5.1")
    print(result)
    print()
    
    # Test 3: Filter by queue 3.2
    print("\nTest 3: Filter by queue 3.2")
    print("-" * 60)
    result = format_schedule(data, "3.2")
    print(result)
    print()
    
    # Test 4: Invalid queue
    print("\nTest 4: Invalid queue (99.9)")
    print("-" * 60)
    result = format_schedule(data, "99.9")
    print(result)
    print()
    
    print("="*60)
    print("✅ Queue filtering tests completed!")

if __name__ == '__main__':
    test_queue_filtering()
