#!/usr/bin/env python3
"""
Dry run test - verify bot functions without connecting to Telegram
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from bot import fetch_schedule, format_schedule, minutes_to_time

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
    print("\n" + "="*60)
    print("FORMATTED OUTPUT:")
    print("="*60)
    print(formatted[:1000])  # Show first 1000 chars
    if len(formatted) > 1000:
        print(f"\n... (truncated, total {len(formatted)} chars)")


async def main():
    """Run all tests"""
    print("🚀 Starting bot dry run tests\n")
    print("="*60)
    
    # Test 1: Time converter
    test_time_converter()
    
    # Test 2: API fetch
    data = await test_api_fetch()
    
    # Test 3: Formatter
    test_formatter(data)
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("\nNext step: Configure .env and run the actual bot with:")
    print("  python bot.py")


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
