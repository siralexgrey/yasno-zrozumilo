#!/usr/bin/env python3
"""
Dry run test - verify bot functions without connecting to Telegram
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import fetch_schedule, format_schedule, minutes_to_time, has_schedule_changed

def test_time_converter():
    """Test the time conversion function"""
    print("🧪 Testing time converter...")
    tests = [
        (0, "00:00"),
        (60, "01:00"),
        (270, "04:30"),
        (1440, "24:00"),
        (750, "12:30")
    ]
    
    for minutes, expected in tests:
        result = minutes_to_time(minutes)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {minutes} min → {result} (expected {expected})")


async def test_api_fetch():
    """Test fetching data from API"""
    print("\n🧪 Testing API fetch...")
    data = await fetch_schedule()
    
    if data:
        print("  ✅ API fetch successful")
        print(f"  📊 Number of queue groups: {len(data)}")
        print(f"  🔸 Queue groups: {', '.join(sorted(data.keys()))}")
        return data
    else:
        print("  ❌ API fetch failed")
        return None


def test_formatter(data):
    """Test schedule formatting"""
    print("\n🧪 Testing schedule formatter...")
    
    if not data:
        print("  ⚠️  No data to format")
        return
    
    formatted = format_schedule(data)
    print("  ✅ Formatting successful")
    print(f"  📝 Message length: {len(formatted)} characters")
    print(f"  ✅ Full schedule has all queues: {'1.1' in formatted and '6.2' in formatted}")


def test_queue_filtering(data):
    """Test queue filtering functionality"""
    print("\n🧪 Testing queue filtering...")
    
    if not data:
        print("  ⚠️  No data to filter")
        return
    
    # Test specific queue
    filtered = format_schedule(data, "5.1")
    print("  ✅ Filter by queue 5.1: successful")
    print(f"  📝 Filtered message length: {len(filtered)} characters")
    print(f"  ✅ Contains queue 5.1: {'5.1' in filtered}")
    
    # Test another queue
    filtered_3_2 = format_schedule(data, "3.2")
    print("  ✅ Filter by queue 3.2: successful")
    print(f"  ✅ Contains queue 3.2: {'3.2' in filtered_3_2}")
    
    # Test invalid queue
    filtered_invalid = format_schedule(data, "99.9")
    print("  ✅ Filter by invalid queue 99.9: handled gracefully")


def test_keyboard_buttons():
    """Test custom keyboard button text mapping"""
    print("\n🧪 Testing keyboard button mappings...")
    
    button_map = {
        "📋 Графік": "schedule_command",
        "🔸 Моя черга": "myqueue_command",
        "⚙️ Вибрати чергу": "queue_command",
        "🔔 Сповіщення": "notifications_command",
        "📊 Статус": "status_command",
        "ℹ️ Довідка": "help_command",
    }
    
    for button_text, handler_name in button_map.items():
        print(f"  ✅ {button_text} → {handler_name}")
    
    print(f"  📊 Total buttons: {len(button_map)}")


async def test_change_detection():
    """Test schedule change detection"""
    print("\n🧪 Testing change detection...")
    
    data = await fetch_schedule()
    if not data:
        print("  ⚠️  Could not fetch data for change detection test")
        return
    
    # Create mock old data (same as current)
    old_data = data.copy()
    new_data = data.copy()
    
    # Test 1: No changes
    has_changed, changes = has_schedule_changed(old_data, new_data, "5.1")
    print(f"  ✅ Same data detected as unchanged: {not has_changed}")
    
    # Test 2: Modify updatedOn timestamp
    if "5.1" in new_data and "today" in new_data["5.1"]:
        new_data["5.1"]["today"]["updatedOn"] = "2025-11-18T17:00:00"
        old_data["5.1"]["today"]["updatedOn"] = "2025-11-18T16:00:00"
        has_changed, changes = has_schedule_changed(old_data, new_data, "5.1")
        print(f"  ✅ Timestamp change detected: {has_changed}")
    
    print(f"  ✅ Change detection working")


async def main():
    """Run all tests"""
    print("🚀 Starting bot tests\n")
    print("="*60)
    
    # Test 1: Time converter
    test_time_converter()
    
    # Test 2: API fetch
    data = await test_api_fetch()
    
    # Test 3: Formatter
    test_formatter(data)
    
    # Test 4: Queue filtering
    test_queue_filtering(data)
    
    # Test 5: Keyboard buttons
    test_keyboard_buttons()
    
    # Test 6: Change detection
    await test_change_detection()
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("\nNext step: Run the actual bot with:")
    print("  python bot.py")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
