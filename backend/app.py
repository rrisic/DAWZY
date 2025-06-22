#!/usr/bin/env python3
"""
Music Production Assistant Backend
Handles LLM processing, OpenAI Whisper transcription, and REAPER integration using reapy
"""

import json
import sys
import logging
import threading
import time
import asyncio
import websockets
import base64
import io
from datetime import datetime
import random
import os
from typing import Dict, Any, List
import wave
import tempfile

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    import os
    # Load .env from the backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(backend_dir, '.env')
    load_dotenv(env_path)
except ImportError:
    print("Warning: python-dotenv not found. Install with: pip install python-dotenv")

# OpenAI API
try:
    from openai import OpenAI
except ImportError:
    print("Error: openai not found. Please install with: pip install openai")
    OpenAI = None

# Flask for HTTP endpoints
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    print("Error: flask not found. Please install with: pip install flask flask-cors")
    Flask = None

# Import reapy instead of ReaScript API
try:
    import reapy
    from reapy import reascript_api as RPR
except ImportError:
    print("Error: reapy not found. Please install with: pip install python-reapy")
    # Fallback for testing outside REAPER
    def RPR_ShowConsoleMsg(msg):
        print(msg)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global conversation history (in production, you'd want to store this per user/session)
conversation_history = []
MAX_HISTORY = 10  # Keep last 10 messages for context

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio using OpenAI Whisper"""
    try:
        data = request.get_json()
        if not data or 'audio' not in data:
            return jsonify({'success': False, 'error': 'No audio data provided'})
        
        # Decode base64 audio
        audio_data = base64.b64decode(data['audio'])
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        try:
            # Transcribe using OpenAI Whisper
            if not OpenAI:
                return jsonify({'success': False, 'error': 'OpenAI not available'})
            
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            with open(temp_file_path, 'rb') as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info(f"Transcription successful: {transcript}")
            
            return jsonify({
                'success': True,
                'transcript': transcript
            })
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/tts', methods=['POST'])
def text_to_speech():
    """Convert text to speech using OpenAI TTS"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'success': False, 'error': 'No text provided'})
        
        text = data['text']
        logger.info(f"Converting to speech: {text}")
        
        if not OpenAI:
            return jsonify({'success': False, 'error': 'OpenAI not available'})
        
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Generate speech using OpenAI TTS
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",  # Options: alloy, echo, fable, onyx, nova, shimmer
            input=text
        )
        
        # Convert to base64 for sending to frontend
        audio_data = response.content
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        logger.info(f"TTS successful for text: {text[:50]}...")
        
        return jsonify({
            'success': True,
            'audio': audio_base64,
            'text': text
        })
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat', methods=['POST'])
def chat_message():
    """Handle chat messages with OpenAI GPT"""
    global conversation_history  # Declare as global
    
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'success': False, 'error': 'No message provided'})
        
        message = data['message']
        logger.info(f"Received chat message: {message}")
        
        # Use OpenAI GPT for intelligent responses
        if not OpenAI:
            response = "I'm sorry, but I'm not able to process your request right now. Please try again later."
        else:
            try:
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                
                # Create a conversation context for music production
                system_prompt = """You are DAWZY, a helpful music production assistant specializing in the REAPER DAW. You can help with:

- REAPER workflow questions and tutorials
- Audio production techniques and best practices
- Track management and organization
- Effects and processing chains
- MIDI and audio editing
- Automation and mixing
- Music theory and composition
- Sound design and synthesis

Be helpful, concise, and focus on practical music production advice. If someone asks about creating tracks, melodies, or specific REAPER features, provide detailed, actionable guidance. Keep responses conversational but informative."""

                # Build messages array with system prompt and conversation history
                messages = [{"role": "system", "content": system_prompt}]
                
                # Add conversation history for context
                for msg in conversation_history[-MAX_HISTORY:]:
                    messages.append(msg)
                
                # Add current user message
                messages.append({"role": "user", "content": message})
                
                # Get response from OpenAI GPT
                gpt_response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=200,
                    temperature=0.7
                )
                
                response = gpt_response.choices[0].message.content.strip()
                logger.info(f"GPT response: {response}")
                
                # Update conversation history
                conversation_history.append({"role": "user", "content": message})
                conversation_history.append({"role": "assistant", "content": response})
                
                # Keep only the last MAX_HISTORY messages
                if len(conversation_history) > MAX_HISTORY * 2:  # *2 because each exchange has 2 messages
                    conversation_history = conversation_history[-MAX_HISTORY * 2:]
                
            except Exception as e:
                logger.error(f"OpenAI GPT error: {e}")
                response = "I'm having trouble processing your request right now. Please try again."
        
        # Generate TTS for the response
        try:
            if OpenAI:
                client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                tts_response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",
                    input=response
                )
                audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                logger.info(f"Generated TTS for response: {response[:50]}...")
            else:
                audio_base64 = None
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            audio_base64 = None
        
        return jsonify({
            'success': True,
            'response': response,
            'audio': audio_base64
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear-conversation', methods=['POST'])
def clear_conversation():
    """Clear conversation history"""
    try:
        global conversation_history
        conversation_history.clear()
        logger.info("Conversation history cleared")
        
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    print("Starting Music Production Assistant Backend...")
    print("Available services:")
    print("- OpenAI Whisper transcription: http://localhost:5000/transcribe")
    print("- Text-to-speech: http://localhost:5000/tts")
    print("- Chat messages: http://localhost:5000/chat")
    print("- Clear conversation: http://localhost:5000/clear-conversation")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
