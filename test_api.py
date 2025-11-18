#!/usr/bin/env python3
"""
Test script to verify API connection and data format
"""

import requests
import json

API_URL = "https://app.yasno.ua/api/blackout-service/public/shutdowns/regions/3/dsos/301/planned-outages"

def test_api():
    """Test the Yasno API endpoint"""
    print("🔍 Testing API connection...")
    print(f"URL: {API_URL}\n")
    
    try:
        response = requests.get(API_URL, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n📦 Response data structure:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            print("\n" + "="*50)
            print("✅ API is working correctly!")
            print("="*50)
        else:
            print(f"\n⚠️  Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check your internet connection")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    except json.JSONDecodeError:
        print("❌ Invalid JSON response")
        print(f"Response text: {response.text}")

if __name__ == '__main__':
    test_api()
