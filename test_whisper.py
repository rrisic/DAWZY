#!/usr/bin/env python3
"""
Test script for OpenAI Whisper integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

def test_openai_key():
    """Test if OpenAI API key is configured"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in backend/.env")
        print("Please add your OpenAI API key to backend/.env:")
        print("OPENAI_API_KEY=your_openai_api_key_here")
        return False
    
    print("✅ OPENAI_API_KEY found")
    return True

def test_dependencies():
    """Test if required dependencies are installed"""
    try:
        from openai import OpenAI
        print("✅ OpenAI library available")
    except ImportError:
        print("❌ OpenAI library not found")
        print("Install with: pip install openai")
        return False
    
    try:
        from flask import Flask
        print("✅ Flask library available")
    except ImportError:
        print("❌ Flask library not found")
        print("Install with: pip install flask flask-cors")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing OpenAI Whisper Integration...")
    print("=" * 40)
    
    if test_openai_key() and test_dependencies():
        print("\n✅ All tests passed!")
        print("You can now start the backend with: python backend/app.py")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)