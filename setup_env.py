#!/usr/bin/env python3
"""
Setup script to create .env file for DAWZY backend
"""

import os

def create_env_file():
    """Create .env file in backend directory"""
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    env_path = os.path.join(backend_dir, '.env')
    
    # Check if .env already exists
    if os.path.exists(env_path):
        print(f".env file already exists at: {env_path}")
        return
    
    # Create .env content
    env_content = """# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Beatoven.ai API Key
BEATOVEN_AI_API_KEY=your_beatoven_ai_api_key_here
"""
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"Created .env file at: {env_path}")
    print("Please update your OpenAI API key in the .env file")

if __name__ == "__main__":
    create_env_file() 