#!/usr/bin/env python3
"""
Test script for Beatoven.ai music generation API
"""

import os
import requests
import time
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_beatoven_ai():
    """Test Beatoven.ai API connection and music generation"""
    
    print("🎵 Testing Beatoven.ai Music Generation API")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('BEATOVEN_AI_API_KEY')
    if not api_key:
        print("❌ Error: BEATOVEN_AI_API_KEY not found in environment variables")
        print("Please add your Beatoven.ai API key to the .env file")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test API connection with a simple composition request
    test_prompt = "30 seconds peaceful lo-fi chill hop track"
    
    payload = {
        "prompt": {
            "text": test_prompt
        },
        "format": "wav",
        "looping": False
    }
    
    print(f"\n📝 Testing composition request...")
    print(f"Prompt: {test_prompt}")
    
    try:
        # Send composition request
        response = requests.post(
            "https://public-api.beatoven.ai/api/v1/tracks/compose",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ Composition request successful!")
            print(f"Response: {json.dumps(response_data, indent=2)}")
            
            if response_data.get('status') in ['started', 'composing'] and 'task_id' in response_data:
                task_id = response_data['task_id']
                print(f"\n🔄 Task ID: {task_id}")
                print("Testing status polling...")
                
                # Test status polling (just a few attempts)
                for attempt in range(3):
                    time.sleep(2)
                    
                    status_response = requests.get(
                        f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}",
                        headers={"Authorization": f"Bearer {api_key}"},
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status')
                        print(f"Status check {attempt + 1}: {status}")
                        
                        if status == 'composed':
                            print("✅ Track composition completed!")
                            track_url = status_data.get('meta', {}).get('track_url')
                            if track_url:
                                print(f"Track URL: {track_url}")
                            break
                        elif status in ['failed', 'error']:
                            print(f"❌ Composition failed: {status_data}")
                            break
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        break
                
                print("\n✅ Beatoven.ai API is working correctly!")
                return True
            else:
                print(f"❌ Unexpected response format: {response_data}")
                return False
                
        elif response.status_code == 401:
            print("❌ Authentication failed - check your API key")
            return False
        elif response.status_code == 400:
            print("❌ Bad request - check your payload format")
            print(f"Response: {response.text}")
            return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_environment():
    """Test environment setup"""
    print("🔧 Testing Environment Setup")
    print("=" * 30)
    
    # Check required packages
    try:
        import requests
        print("✅ requests package available")
    except ImportError:
        print("❌ requests package not available")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv package available")
    except ImportError:
        print("❌ python-dotenv package not available")
        return False
    
    # Check .env file
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
        return False
    
    return True

def test_prompt_engineering():
    """Test the improved prompt engineering with different scenarios"""
    
    print("🧠 Testing Prompt Engineering")
    print("=" * 40)
    
    # Import the function from app.py
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    
    try:
        from app import create_instrument_aware_prompt
        
        test_cases = [
            "create a techno track with heavy bass",
            "generate an 80s rock song without drums",
            "make a peaceful ambient melody",
            "produce a jazz track without guitar",
            "create a hip hop beat",
            "generate a classical piano piece"
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test Case {i}: {test_case}")
            print("-" * 50)
            
            prompt = create_instrument_aware_prompt(test_case)
            print("Generated Prompt:")
            print(prompt)
            print("\n" + "="*60)
            
    except ImportError as e:
        print(f"❌ Could not import function: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🎵 Beatoven.ai API Test Suite")
    print("=" * 40)
    
    # Test environment
    if not test_environment():
        print("\n❌ Environment test failed. Please check your setup.")
        exit(1)
    
    print("\n" + "=" * 40)
    
    # Test prompt engineering
    if test_prompt_engineering():
        print("\n✅ Prompt engineering test passed!")
    
    print("\n" + "=" * 40)
    
    # Test API
    if test_beatoven_ai():
        print("\n🎉 All tests passed! Beatoven.ai is ready to use.")
    else:
        print("\n❌ API test failed. Please check your configuration.")
        exit(1) 