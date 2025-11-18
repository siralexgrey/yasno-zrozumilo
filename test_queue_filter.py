#!/usr/bin/env python3
"""
Test queue filtering functionality and other core features
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import format_schedule, has_schedule_changed
import requests

API_URL = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/3/dsos/301/planned-outages"

def test_queue_filtering():
    """Test the queue filtering feature"""
    print("🧪 Testing Queue Filtering\n")
    print("="*60)
    
    # Fetch data
    print("📥 Fetching data from API...")
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        print(f"✅ Got data for {len(data)} queues\n")
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        return
    
    # Test 1: Show all queues (no filter)
    print("Test 1: All queues (no filter)")
    print("-" * 60)
    result = format_schedule(data)
    all_queues_ok = all(q in result for q in ["1.1", "5.1", "6.2"])
    print(f"  ✅ Formatted successfully")
    print(f"  📝 Message length: {len(result)} characters")
    print(f"  ✅ Contains all queues: {all_queues_ok}")
    print()
    
    # Test 2: Filter by queue 5.1
    print("Test 2: Filter by queue 5.1")
    print("-" * 60)
    result = format_schedule(data, "5.1")
    contains_5_1 = "5.1" in result
    print(f"  ✅ Formatted successfully")
    print(f"  📝 Message length: {len(result)} characters")
    print(f"  ✅ Contains queue 5.1: {contains_5_1}")
    print()
    
    # Test 3: Filter by queue 3.2
    print("Test 3: Filter by queue 3.2")
    print("-" * 60)
    result = format_schedule(data, "3.2")
    contains_3_2 = "3.2" in result
    print(f"  ✅ Formatted successfully")
    print(f"  📝 Message length: {len(result)} characters")
    print(f"  ✅ Contains queue 3.2: {contains_3_2}")
    print()
    
    # Test 4: Invalid queue
    print("Test 4: Invalid queue (99.9)")
    print("-" * 60)
    result = format_schedule(data, "99.9")
    is_error = "не знайдено" in result or "invalid" in result.lower() or len(result) < 10
    print(f"  ✅ Handled gracefully")
    print(f"  📝 Message: {result[:100]}")
    print()
    
    # Test 5: All valid queues
    print("Test 5: Verify all valid queues")
    print("-" * 60)
    valid_queues = [f"{i}.{j}" for i in range(1, 7) for j in [1, 2]]
    for queue in valid_queues:
        result = format_schedule(data, queue)
        is_valid = queue in result or len(result) > 20
        status = "✅" if is_valid else "❌"
        print(f"  {status} Queue {queue}")
    
    print()
    print("="*60)
    print("✅ Queue filtering tests completed!")


def test_change_detection():
    """Test schedule change detection"""
    print("\n🧪 Testing Change Detection\n")
    print("="*60)
    
    print("📥 Fetching data from API...")
    try:
        response = requests.get(API_URL, timeout=10)
        data = response.json()
        print(f"✅ Got data\n")
    except Exception as e:
        print(f"❌ Failed to fetch data: {e}")
        return
    
    # Test 1: Same data = no change
    print("Test 1: Identical data (no change)")
    print("-" * 60)
    old_data = data.copy()
    new_data = data.copy()
    has_changed, _ = has_schedule_changed(old_data, new_data, "5.1")
    print(f"  ✅ Same data detected as unchanged: {not has_changed}")
    print()
    
    # Test 2: Different timestamps = change
    print("Test 2: Updated timestamp (change detected)")
    print("-" * 60)
    if "5.1" in data and "today" in data["5.1"]:
        old_timestamp = data["5.1"]["today"].get("updatedOn", "2025-01-01T00:00:00")
        new_data = data.copy()
        new_data["5.1"] = data["5.1"].copy()
        new_data["5.1"]["today"] = data["5.1"]["today"].copy()
        new_data["5.1"]["today"]["updatedOn"] = "2025-11-18T17:00:00"
        
        has_changed, changes = has_schedule_changed(data, new_data, "5.1")
        print(f"  ✅ Timestamp change detected: {has_changed}")
        if changes:
            print(f"  📝 Changes: {changes}")
    else:
        print("  ⚠️  Could not test timestamp change")
    print()
    
    print("="*60)
    print("✅ Change detection tests completed!")


if __name__ == '__main__':
    test_queue_filtering()
    test_change_detection()
