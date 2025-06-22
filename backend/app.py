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
import numpy as np

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

# Beatoven.ai for music generation
import requests

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

# Import REAPER controller
try:
    from reapy_actions import ReaperController
    reaper_controller = ReaperController()
    logger.info("REAPER Controller initialized successfully")
except ImportError:
    print("Warning: Could not import ReaperController from reapy_actions.py")
    reaper_controller = None
except Exception as e:
    logger.error(f"Failed to initialize REAPER Controller: {e}")
    reaper_controller = None

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global conversation history (in production, you'd want to store this per user/session)
conversation_history = []
MAX_HISTORY = 10  # Keep last 10 messages for context

def detect_reaper_action(message: str) -> bool:
    """
    Detect if a user message requires REAPER actions
    Returns True if the message should be routed to the REAPER controller
    """
    message_lower = message.lower()
    
    # REAPER-specific keywords and phrases
    reaper_keywords = [
        # Track operations
        'add track', 'create track', 'new track', 'delete track', 'remove track',
        'list tracks', 'show tracks', 'track named', 'track called',
        
        # FX operations  
        'add fx', 'add effect', 'add plugin', 'remove fx', 'remove effect',
        'fx parameter', 'effect parameter', 'plugin parameter',
        'set parameter', 'adjust parameter', 'modify parameter',
        'compressor', 'reverb', 'delay', 'eq', 'synthesizer', 'synth',
        'reasynth', 'reaeq', 'reacomp', 'rea', 'vst',
        
        # MIDI operations
        'add note', 'add midi', 'midi note', 'transpose', 'pitch',
        'note data', 'midi data', 'chord', 'melody line',
        
        # REAPER-specific terms
        'reaper', 'daw', 'project', 'session', 'timeline',
        'automation', 'routing', 'send', 'bus'
    ]
    
    # Check for any REAPER keywords
    for keyword in reaper_keywords:
        if keyword in message_lower:
            return True
    
    # Check for action-oriented phrases with music terms
    action_phrases = ['create', 'add', 'make', 'set up', 'configure', 'adjust', 'modify', 'change']
    music_terms = ['track', 'channel', 'fx', 'effect', 'plugin', 'parameter', 'midi', 'note']
    
    for action in action_phrases:
        for term in music_terms:
            if action in message_lower and term in message_lower:
                return True
    
    return False

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
        
        # Check if this is a REAPER action request
        if detect_reaper_action(message) and reaper_controller:
            logger.info("Detected REAPER action request - routing to Claude controller")
            try:
                # Use Claude-powered REAPER controller for DAW operations
                reaper_response = reaper_controller.process_query_with_chaining(message)
                
                # Generate TTS for the REAPER response
                try:
                    if OpenAI:
                        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                        tts_response = client.audio.speech.create(
                            model="tts-1",
                            voice="alloy",
                            input=reaper_response
                        )
                        audio_base64 = base64.b64encode(tts_response.content).decode('utf-8')
                        logger.info(f"Generated TTS for REAPER response")
                    else:
                        audio_base64 = None
                except Exception as e:
                    logger.error(f"TTS generation failed for REAPER response: {e}")
                    audio_base64 = None
                
                # Update conversation history with REAPER interaction
                conversation_history.append({"role": "user", "content": message})
                conversation_history.append({"role": "assistant", "content": reaper_response})
                
                # Keep only the last MAX_HISTORY messages
                if len(conversation_history) > MAX_HISTORY * 2:
                    conversation_history = conversation_history[-MAX_HISTORY * 2:]
                
                return jsonify({
                    'success': True,
                    'response': reaper_response,
                    'audio': audio_base64,
                    'reaper_action': True,
                    'music_generation': None
                })
                
            except Exception as e:
                logger.error(f"REAPER controller error: {e}")
                response = f"I encountered an error while performing the REAPER action: {str(e)}"
        
        # Use OpenAI GPT for intelligent responses
        elif not OpenAI:
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
- AI-powered music generation using Beatoven.ai

IMPORTANT: When users request music generation, you MUST respond with a JSON object. Look for these keywords and phrases:
- "generate", "create", "make", "produce"
- "track", "beat", "melody", "bass", "drum", "snare", "kick", "hi-hat"
- "music", "song", "rhythm", "pattern"
- "bpm", "tempo", "key", "genre"

Examples of requests that should trigger music generation:
- "can you generate me a snare drumline please"
- "create a techno track with heavy bass"
- "make a beat at 120 bpm"
- "generate a peaceful ambient melody"
- "produce a dark techno track"
- "create an 80s rock song without drums"

INSTRUMENT COVERAGE GUIDELINES:
- By default, include ALL essential instruments: drums, bass, rhythm, lead melody, harmony
- Only exclude instruments if the user specifically requests it (e.g., "without drums", "no bass")
- Always create complete instrumental arrangements unless specified otherwise
- Focus on musical composition, not vocals or lyrics

When you detect a music generation request, respond with this exact JSON format:
{
  "action": "generate_music",
  "instructions": "detailed music generation instructions including tempo, genre, instruments, and any specific exclusions",
  "response": "your helpful response about the music generation"
}

For regular questions about REAPER, music theory, or production techniques, respond normally without JSON formatting.

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
                
                # Check if this is a music generation request
                music_generation_result = None
                try:
                    # Try to parse as JSON to check for music generation action
                    response_data = json.loads(response)
                    if response_data.get('action') == 'generate_music':
                        logger.info("Detected music generation request")
                        
                        # Generate music using Beatoven.ai
                        music_response = generate_music_internal(response_data.get('instructions', ''))
                        if music_response.get('success'):
                            music_generation_result = music_response
                            response = response_data.get('response', 'Music generation completed!')
                        else:
                            response = f"Music generation failed: {music_response.get('error', 'Unknown error')}"
                            
                except (json.JSONDecodeError, KeyError) as e:
                    # Not a music generation request or invalid JSON, use normal response
                    logger.info(f"Not a music generation request or JSON parsing failed: {e}")
                    pass
                
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
            'audio': audio_base64,
            'music_generation': music_generation_result
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

@app.route('/reaper-action', methods=['POST'])
def reaper_action():
    """Handle REAPER-specific actions using Claude controller"""
    try:
        data = request.get_json()
        if not data or 'action' not in data:
            return jsonify({'success': False, 'error': 'No action provided'})
        
        action = data['action']
        logger.info(f"Received REAPER action: {action}")
        
        if not reaper_controller:
            return jsonify({'success': False, 'error': 'REAPER controller not available'})
        
        # Use Claude-powered REAPER controller
        try:
            result = reaper_controller.process_query_with_chaining(action)
            logger.info(f"REAPER action completed: {result[:100]}...")
            
            return jsonify({
                'success': True,
                'result': result,
                'action': action
            })
            
        except Exception as e:
            logger.error(f"REAPER action error: {e}")
            return jsonify({'success': False, 'error': str(e)})
        
    except Exception as e:
        logger.error(f"REAPER action endpoint error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/generate-music', methods=['POST'])
def generate_music():
    """Generate music using Beatoven.ai"""
    try:
        data = request.get_json()
        if not data or 'instructions' not in data:
            return jsonify({'success': False, 'error': 'No instructions provided'})
        
        instructions = data['instructions']
        logger.info(f"Generating music with instructions: {instructions}")
        
        if not requests:
            return jsonify({'success': False, 'error': 'Beatoven.ai not available'})
        
        # Configure Beatoven.ai
        api_key = os.getenv('BEATOVEN_AI_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'Beatoven.ai API key not found'})
        
        # Create structured prompt for Beatoven.ai
        beatoven_prompt = create_instrument_aware_prompt(instructions)
        
        # Prepare the request payload for Beatoven.ai music generation
        payload = {
            "prompt": {
                "text": beatoven_prompt
            },
            "format": "wav",
            "looping": False
        }
        
        # Send the request to Beatoven.ai music generation API
        response = requests.post(
            "https://public-api.beatoven.ai/api/v1/tracks/compose",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Beatoven.ai request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return jsonify({'success': False, 'error': f"Beatoven.ai request failed: {response.text}"})
        
        # Parse the response to get task_id
        response_data = response.json()
        if response_data.get('status') not in ['started', 'composing'] or 'task_id' not in response_data:
            logger.error(f"Invalid Beatoven.ai response: {response_data}")
            return jsonify({'success': False, 'error': 'Invalid response from Beatoven.ai'})
        
        task_id = response_data['task_id']
        logger.info(f"Beatoven.ai composition started with task_id: {task_id}")
        
        # Poll for completion (with timeout)
        max_attempts = 60  # 5 minutes with 5-second intervals
        for attempt in range(max_attempts):
            time.sleep(5)  # Wait 5 seconds between checks
            
            # Check task status
            status_response = requests.get(
                f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if status_response.status_code != 200:
                logger.error(f"Status check failed: {status_response.status_code}")
                continue
            
            status_data = status_response.json()
            status = status_data.get('status')
            
            logger.info(f"Task status: {status} (attempt {attempt + 1}/{max_attempts})")
            
            if status == 'composed':
                # Download the generated track
                track_url = status_data.get('meta', {}).get('track_url')
                if not track_url:
                    return jsonify({'success': False, 'error': 'No track URL in response'})
                
                # Download the audio file
                audio_response = requests.get(track_url)
                if audio_response.status_code != 200:
                    return jsonify({'success': False, 'error': 'Failed to download audio file'})
                
                audio_data = audio_response.content
                
                # Generate filename based on user input
                filename_base = create_filename_from_prompt(instructions)
                output_filename = f"{filename_base}.wav"
                output_path = os.path.join(os.path.dirname(__file__), 'generated_music', output_filename)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save the audio file
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                
                logger.info(f"Generated music file: {output_path}")
                
                # Import into REAPER if available
                try:
                    if 'reapy' in sys.modules:
                        project = reapy.Project()
                        
                        # Add the generated audio file to REAPER
                        track = project.add_track()
                        track.add_item(0, output_path)
                        
                        logger.info(f"Added {output_filename} to REAPER")
                        
                except Exception as e:
                    logger.warning(f"Could not import to REAPER: {e}")
                
                return jsonify({
                    'success': True,
                    'message': f'Generated music track: {output_filename}',
                    'file_path': output_path,
                    'structured_instructions': {
                        'description': instructions,
                        'task_id': task_id,
                        'format': 'wav'
                    }
                })
            
            elif status in ['failed', 'error']:
                return jsonify({'success': False, 'error': f'Beatoven.ai composition failed: {status_data}'})
        
        # Timeout
        return jsonify({'success': False, 'error': 'Beatoven.ai composition timed out'})
        
    except Exception as e:
        logger.error(f"Music generation error: {e}")
        return jsonify({'success': False, 'error': str(e)})

def generate_music_internal(instructions):
    """Internal function to generate music using Beatoven.ai"""
    try:
        logger.info(f"Generating music with instructions: {instructions}")
        
        if not requests:
            return {'success': False, 'error': 'Beatoven.ai not available'}
        
        # Configure Beatoven.ai
        api_key = os.getenv('BEATOVEN_AI_API_KEY')
        if not api_key:
            return {'success': False, 'error': 'Beatoven.ai API key not found'}
        
        # Create structured prompt for Beatoven.ai
        beatoven_prompt = create_instrument_aware_prompt(instructions)
        
        # Prepare the request payload for Beatoven.ai music generation
        payload = {
            "prompt": {
                "text": beatoven_prompt
            },
            "format": "wav",
            "looping": False
        }
        
        # Send the request to Beatoven.ai music generation API
        response = requests.post(
            "https://public-api.beatoven.ai/api/v1/tracks/compose",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Beatoven.ai request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {'success': False, 'error': f"Beatoven.ai request failed: {response.text}"}
        
        # Parse the response to get task_id
        response_data = response.json()
        if response_data.get('status') not in ['started', 'composing'] or 'task_id' not in response_data:
            logger.error(f"Invalid Beatoven.ai response: {response_data}")
            return {'success': False, 'error': 'Invalid response from Beatoven.ai'}
        
        task_id = response_data['task_id']
        logger.info(f"Beatoven.ai composition started with task_id: {task_id}")
        
        # Poll for completion (with timeout)
        max_attempts = 60  # 5 minutes with 5-second intervals
        for attempt in range(max_attempts):
            time.sleep(5)  # Wait 5 seconds between checks
            
            # Check task status
            status_response = requests.get(
                f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if status_response.status_code != 200:
                logger.error(f"Status check failed: {status_response.status_code}")
                continue
            
            status_data = status_response.json()
            status = status_data.get('status')
            
            logger.info(f"Task status: {status} (attempt {attempt + 1}/{max_attempts})")
            
            if status == 'composed':
                # Download the generated track
                track_url = status_data.get('meta', {}).get('track_url')
                if not track_url:
                    return {'success': False, 'error': 'No track URL in response'}
                
                # Download the audio file
                audio_response = requests.get(track_url)
                if audio_response.status_code != 200:
                    return {'success': False, 'error': 'Failed to download audio file'}
                
                audio_data = audio_response.content
                
                # Generate filename based on user input
                filename_base = create_filename_from_prompt(instructions)
                output_filename = f"{filename_base}.wav"
                output_path = os.path.join(os.path.dirname(__file__), 'generated_music', output_filename)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save the audio file
                with open(output_path, 'wb') as f:
                    f.write(audio_data)
                
                logger.info(f"Generated music file: {output_path}")
                
                # Import into REAPER if available
                try:
                    if 'reapy' in sys.modules:
                        project = reapy.Project()
                        
                        # Add the generated audio file to REAPER
                        track = project.add_track()
                        track.add_item(0, output_path)
                        
                        logger.info(f"Added {output_filename} to REAPER")
                        
                except Exception as e:
                    logger.warning(f"Could not import to REAPER: {e}")
                
                return {
                    'success': True,
                    'message': f'Generated music track: {output_filename}',
                    'file_path': output_path,
                    'structured_instructions': {
                        'description': instructions,
                        'task_id': task_id,
                        'format': 'wav'
                    }
                }
            
            elif status in ['failed', 'error']:
                return {'success': False, 'error': f'Beatoven.ai composition failed: {status_data}'}
        
        # Timeout
        return {'success': False, 'error': 'Beatoven.ai composition timed out'}
        
    except Exception as e:
        logger.error(f"Music generation error: {e}")
        return {'success': False, 'error': str(e)}

def create_filename_from_prompt(prompt):
    """Create a filename based on the user's prompt"""
    # Clean the prompt for filename use
    import re
    
    # Remove special characters and convert to lowercase
    clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', prompt.lower())
    
    # Replace spaces with underscores
    clean_name = re.sub(r'\s+', '_', clean_name)
    
    # Limit length and remove leading/trailing underscores
    clean_name = clean_name.strip('_')[:50]
    
    # Add timestamp to ensure uniqueness
    timestamp = int(time.time())
    
    return f"{clean_name}_{timestamp}"

def generate_dynamic_audio(structured_instructions, sample_rate, duration):
    """Generate more dynamic audio based on structured instructions"""
    import numpy as np
    
    # Extract parameters from structured instructions
    tempo = structured_instructions.get('tempo', 120)
    genre = structured_instructions.get('genre', 'electronic').lower()
    mood = structured_instructions.get('mood', 'energetic').lower()
    instruments = structured_instructions.get('instruments', ['synth', 'drums', 'bass'])
    
    # Calculate samples needed
    total_samples = int(sample_rate * duration)
    
    # Initialize audio array
    audio_data = np.zeros(total_samples)
    
    # Generate different audio based on genre and mood
    if 'drum' in ' '.join(instruments).lower() or 'beat' in ' '.join(instruments).lower() or 'snare' in ' '.join(instruments).lower():
        # Generate drum-like pattern
        audio_data = generate_drum_pattern(sample_rate, duration, tempo, mood)
    elif 'bass' in ' '.join(instruments).lower():
        # Generate bass line
        audio_data = generate_bass_line(sample_rate, duration, tempo, mood)
    elif 'melody' in ' '.join(instruments).lower() or 'synth' in ' '.join(instruments).lower():
        # Generate melodic content
        audio_data = generate_melody(sample_rate, duration, tempo, mood)
    else:
        # Generate ambient/pad-like content
        audio_data = generate_ambient_pad(sample_rate, duration, mood)
    
    # Normalize audio
    if np.max(np.abs(audio_data)) > 0:
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.3
    
    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)
    
    return audio_data

def generate_drum_pattern(sample_rate, duration, tempo, mood):
    """Generate a drum pattern"""
    import numpy as np
    
    total_samples = int(sample_rate * duration)
    audio_data = np.zeros(total_samples)
    
    # Calculate beat timing
    beats_per_second = tempo / 60
    samples_per_beat = int(sample_rate / beats_per_second)
    
    # Generate kick drum (low frequency)
    kick_freq = 60
    kick_duration = 0.1  # 100ms
    kick_samples = int(sample_rate * kick_duration)
    
    for i in range(0, total_samples, samples_per_beat):
        if i + kick_samples < total_samples:
            t = np.linspace(0, kick_duration, kick_samples)
            kick = np.sin(2 * np.pi * kick_freq * t) * np.exp(-5 * t)
            audio_data[i:i+kick_samples] += kick * 0.5
    
    # Generate snare drum (mid frequency with noise)
    snare_freq = 200
    snare_duration = 0.15  # 150ms
    snare_samples = int(sample_rate * snare_duration)
    
    for i in range(samples_per_beat // 2, total_samples, samples_per_beat):  # On the 2 and 4
        if i + snare_samples < total_samples:
            t = np.linspace(0, snare_duration, snare_samples)
            # Create snare sound with noise component
            snare_tone = np.sin(2 * np.pi * snare_freq * t) * np.exp(-3 * t)
            snare_noise = np.random.normal(0, 1, snare_samples) * np.exp(-8 * t)
            snare = snare_tone + snare_noise * 0.3
            audio_data[i:i+snare_samples] += snare * 0.4
    
    # Generate hi-hat (high frequency)
    hat_freq = 8000
    hat_duration = 0.05  # 50ms
    hat_samples = int(sample_rate * hat_duration)
    
    for i in range(0, total_samples, samples_per_beat // 2):  # Every half beat
        if i + hat_samples < total_samples:
            t = np.linspace(0, hat_duration, hat_samples)
            hat = np.sin(2 * np.pi * hat_freq * t) * np.exp(-20 * t)
            audio_data[i:i+hat_samples] += hat * 0.3
    
    return audio_data

def generate_bass_line(sample_rate, duration, tempo, mood):
    """Generate a bass line"""
    import numpy as np
    
    total_samples = int(sample_rate * duration)
    audio_data = np.zeros(total_samples)
    
    # Bass frequencies based on mood
    if 'dark' in mood or 'heavy' in mood:
        bass_freqs = [55, 65, 73, 82]  # A1, C2, D2, E2
    else:
        bass_freqs = [82, 98, 110, 123]  # E2, G2, A2, B2
    
    # Generate bass pattern
    beats_per_second = tempo / 60
    samples_per_beat = int(sample_rate / beats_per_second)
    
    for i in range(0, total_samples, samples_per_beat):
        if i + samples_per_beat < total_samples:
            freq = np.random.choice(bass_freqs)
            t = np.linspace(0, 1/beats_per_second, samples_per_beat)
            bass_note = np.sin(2 * np.pi * freq * t) * np.exp(-2 * t)
            audio_data[i:i+samples_per_beat] += bass_note * 0.4
    
    return audio_data

def generate_melody(sample_rate, duration, tempo, mood):
    """Generate a melodic line"""
    import numpy as np
    
    total_samples = int(sample_rate * duration)
    audio_data = np.zeros(total_samples)
    
    # Melody frequencies based on mood
    if 'happy' in mood or 'bright' in mood:
        melody_freqs = [440, 494, 523, 587, 659, 698, 784]  # A4 to G5
    elif 'sad' in mood or 'dark' in mood:
        melody_freqs = [220, 247, 262, 294, 330, 349, 392]  # A3 to G4
    else:
        melody_freqs = [330, 370, 415, 440, 494, 523, 587]  # E4 to D5
    
    # Generate melody pattern
    beats_per_second = tempo / 60
    samples_per_beat = int(sample_rate / beats_per_second)
    
    for i in range(0, total_samples, samples_per_beat * 2):  # Every 2 beats
        if i + samples_per_beat < total_samples:
            freq = np.random.choice(melody_freqs)
            t = np.linspace(0, 2/beats_per_second, samples_per_beat * 2)
            melody_note = np.sin(2 * np.pi * freq * t) * np.exp(-1 * t)
            audio_data[i:i+samples_per_beat*2] += melody_note * 0.3
    
    return audio_data

def generate_ambient_pad(sample_rate, duration, mood):
    """Generate ambient pad-like content"""
    import numpy as np
    
    total_samples = int(sample_rate * duration)
    audio_data = np.zeros(total_samples)
    
    # Ambient frequencies based on mood
    if 'peaceful' in mood or 'ambient' in mood:
        pad_freqs = [110, 165, 220, 330]  # A2, E3, A3, E4
    else:
        pad_freqs = [220, 330, 440, 660]  # A3, E4, A4, E5
    
    # Generate layered pad
    for freq in pad_freqs:
        t = np.linspace(0, duration, total_samples)
        pad_layer = np.sin(2 * np.pi * freq * t) * 0.1
        # Add slow modulation
        modulation = np.sin(2 * np.pi * 0.1 * t) * 0.05
        audio_data += pad_layer + modulation
    
    return audio_data

def extract_bpm_from_text(text):
    """Extract BPM from text input"""
    import re
    
    # Look for BPM patterns like "120 bpm", "120BPM", "120 BPM", etc.
    bpm_patterns = [
        r'(\d+)\s*bpm',  # 120 bpm
        r'(\d+)\s*BPM',  # 120 BPM
        r'(\d+)\s*beats?\s*per\s*minute',  # 120 beats per minute
        r'tempo\s*(\d+)',  # tempo 120
        r'(\d+)\s*tempo',  # 120 tempo
    ]
    
    for pattern in bpm_patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                bpm = int(match.group(1))
                if 60 <= bpm <= 200:  # Reasonable BPM range
                    return bpm
            except ValueError:
                continue
    
    return None

def create_fallback_instructions(instructions):
    """Create fallback structured instructions based on user input"""
    import re
    
    # Extract BPM if mentioned
    bpm = extract_bpm_from_text(instructions)
    if not bpm:
        bpm = 120  # Default BPM
    
    # Determine genre and instruments based on keywords
    instructions_lower = instructions.lower()
    
    # Detect instruments
    instruments = []
    if 'snare' in instructions_lower or 'drum' in instructions_lower:
        instruments.append('snare')
        instruments.append('drums')
    if 'bass' in instructions_lower:
        instruments.append('bass')
    if 'melody' in instructions_lower or 'synth' in instructions_lower:
        instruments.append('synth')
    if 'kick' in instructions_lower:
        instruments.append('kick')
    if 'hi-hat' in instructions_lower or 'hihat' in instructions_lower:
        instruments.append('hi-hat')
    
    # Default instruments if none detected
    if not instruments:
        instruments = ['drums', 'bass', 'synth']
    
    # Detect genre
    genre = 'electronic'
    if 'techno' in instructions_lower:
        genre = 'techno'
    elif 'ambient' in instructions_lower:
        genre = 'ambient'
    elif 'drum' in instructions_lower and 'bass' in instructions_lower:
        genre = 'drum and bass'
    
    # Detect mood
    mood = 'energetic'
    if 'dark' in instructions_lower or 'heavy' in instructions_lower:
        mood = 'dark'
    elif 'peaceful' in instructions_lower or 'calm' in instructions_lower:
        mood = 'peaceful'
    elif 'happy' in instructions_lower or 'bright' in instructions_lower:
        mood = 'happy'
    
    # Determine duration
    duration = 30  # Default 30 seconds
    if 'track' in instructions_lower or 'song' in instructions_lower:
        duration = 60  # Full track length
    
    return {
        "genre": genre,
        "tempo": bpm,
        "key": "C major",
        "mood": mood,
        "instruments": instruments,
        "duration": duration,
        "description": instructions
    }

def generate_fallback_audio(structured_instructions, sample_rate, duration):
    """Generate fallback audio if Beatoven.ai fails"""
    import numpy as np
    
    # Extract parameters from structured instructions
    tempo = structured_instructions.get('tempo', 120)
    genre = structured_instructions.get('genre', 'electronic').lower()
    mood = structured_instructions.get('mood', 'energetic').lower()
    instruments = structured_instructions.get('instruments', ['synth', 'drums', 'bass'])
    
    # Calculate samples needed
    total_samples = int(sample_rate * duration)
    
    # Initialize audio array
    audio_data = np.zeros(total_samples)
    
    # Generate different audio based on genre and mood
    if 'drum' in ' '.join(instruments).lower() or 'beat' in ' '.join(instruments).lower() or 'snare' in ' '.join(instruments).lower():
        # Generate drum-like pattern
        audio_data = generate_drum_pattern(sample_rate, duration, tempo, mood)
    elif 'bass' in ' '.join(instruments).lower():
        # Generate bass line
        audio_data = generate_bass_line(sample_rate, duration, tempo, mood)
    elif 'melody' in ' '.join(instruments).lower() or 'synth' in ' '.join(instruments).lower():
        # Generate melodic content
        audio_data = generate_melody(sample_rate, duration, tempo, mood)
    else:
        # Generate ambient/pad-like content
        audio_data = generate_ambient_pad(sample_rate, duration, mood)
    
    # Normalize audio
    if np.max(np.abs(audio_data)) > 0:
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.3
    
    # Convert to 16-bit PCM
    audio_data = (audio_data * 32767).astype(np.int16)
    
    return audio_data

def create_instrument_aware_prompt(user_request):
    """Create a detailed, instrument-aware prompt for Beatoven.ai based on user request"""
    
    # Default instrument layout
    default_instruments = {
        'drums': 'Full drum kit with kick, snare, hi-hats, cymbals, toms',
        'bass': 'Prominent bass line that drives the rhythm',
        'rhythm': 'Rhythm guitar or keys with chord progressions',
        'lead': 'Main melodic instrument (guitar, synth, piano, etc.)',
        'harmony': 'Supporting harmonic elements and textures',
        'effects': 'Reverb, delay, and atmospheric elements'
    }
    
    # Genre-specific instrument adjustments
    user_request_lower = user_request.lower()
    
    # Detect genre and adjust instruments accordingly
    if any(genre in user_request_lower for genre in ['ambient', 'atmospheric', 'peaceful']):
        # Ambient music typically doesn't need heavy drums
        default_instruments['drums'] = 'Subtle, minimal percussion with gentle cymbals and soft toms'
        default_instruments['bass'] = 'Deep, atmospheric bass with long, sustained notes'
        default_instruments['rhythm'] = 'Atmospheric pads and ambient textures'
        default_instruments['lead'] = 'Ethereal melodic instruments (piano, strings, synth)'
        
    elif any(genre in user_request_lower for genre in ['classical', 'piano']):
        # Classical piano pieces are typically solo or minimal
        default_instruments['drums'] = 'No drums - classical piano piece'
        default_instruments['bass'] = 'No bass - classical piano piece'
        default_instruments['rhythm'] = 'No rhythm section - classical piano piece'
        default_instruments['lead'] = 'Solo piano with classical technique and dynamics'
        default_instruments['harmony'] = 'Classical harmonic progressions and voicings'
        
    elif any(genre in user_request_lower for genre in ['jazz']):
        # Jazz typically has specific instrumentation
        default_instruments['drums'] = 'Jazz drum kit with ride cymbal, brushes, and swing feel'
        default_instruments['bass'] = 'Upright bass or electric bass with walking bass lines'
        default_instruments['rhythm'] = 'Piano or guitar with jazz chord voicings'
        default_instruments['lead'] = 'Saxophone, trumpet, or piano for melodic lines'
        
    elif any(genre in user_request_lower for genre in ['hip hop', 'rap']):
        # Hip hop focuses on beats and bass
        default_instruments['drums'] = 'Hip hop drum machine with heavy kick, snare, and hi-hats'
        default_instruments['bass'] = 'Deep, punchy bass with 808-style sounds'
        default_instruments['rhythm'] = 'Sampled loops or minimal chord progressions'
        default_instruments['lead'] = 'Sampled melodies or synth leads'
        
    elif any(genre in user_request_lower for genre in ['techno', 'electronic']):
        # Electronic music uses synthesized sounds
        default_instruments['drums'] = 'Electronic drum machine with kick, snare, hi-hats, and claps'
        default_instruments['bass'] = 'Synthesized bass with filter sweeps and modulation'
        default_instruments['rhythm'] = 'Synthesized arpeggios and rhythmic elements'
        default_instruments['lead'] = 'Synthesized leads with modulation and effects'
        
    elif any(genre in user_request_lower for genre in ['rock', '80s']):
        # Rock music uses traditional rock instrumentation
        default_instruments['drums'] = 'Rock drum kit with powerful kick, snare, and crash cymbals'
        default_instruments['bass'] = 'Electric bass with driving rock bass lines'
        default_instruments['rhythm'] = 'Electric guitar with power chords and rock riffs'
        default_instruments['lead'] = 'Electric guitar solos and melodic lines'
    
    # Analyze user request for instrument exclusions
    excluded_instruments = []
    
    # Check for instrument exclusions
    if any(phrase in user_request_lower for phrase in ['without drums', 'no drums', 'drumless']):
        excluded_instruments.append('drums')
    if any(phrase in user_request_lower for phrase in ['without bass', 'no bass', 'bassless']):
        excluded_instruments.append('bass')
    if any(phrase in user_request_lower for phrase in ['without guitar', 'no guitar', 'guitarless']):
        excluded_instruments.append('rhythm')
        excluded_instruments.append('lead')
    if any(phrase in user_request_lower for phrase in ['without keys', 'no keys', 'keyboardless']):
        excluded_instruments.append('rhythm')
        excluded_instruments.append('lead')
    
    # Build the instrument section
    instrument_section = "INSTRUMENT LAYOUT:\n"
    for instrument, description in default_instruments.items():
        if instrument not in excluded_instruments:
            instrument_section += f"- {description}\n"
    
    if excluded_instruments:
        instrument_section += f"\nEXCLUDED INSTRUMENTS: {', '.join(excluded_instruments).title()}\n"
    
    # Create the comprehensive prompt
    prompt = f"""
Generate a complete, professional instrumental track based on this request: {user_request}

IMPORTANT REQUIREMENTS:
- This is an INSTRUMENTAL track - NO vocals, NO lyrics, NO singing
- Focus on musical composition and arrangement, not vocal elements
- Create a full, balanced arrangement with all specified instruments

{instrument_section}
COMPOSITION GUIDELINES:
- Create dynamic, evolving arrangements with clear sections
- Include proper musical structure (intro, verse, bridge, etc.)
- Ensure all instruments work together harmoniously
- Add variation and progression throughout the track
- Make it sound like professional studio production

STYLE NOTES:
- Match the requested genre and mood precisely
- Use appropriate instrumentation for the style
- Create authentic, genre-appropriate sounds
- Ensure professional mixing and balance
- Make each instrument distinct and well-defined in the mix

PRODUCTION QUALITY:
- Professional studio-grade sound quality
- Clear separation between instruments
- Balanced frequency spectrum
- Dynamic range appropriate for the genre
- Polished, radio-ready production
"""
    
    return prompt.strip()

if __name__ == "__main__":
    print("Starting Music Production Assistant Backend...")
    print("Available services:")
    print("- OpenAI Whisper transcription: http://localhost:5000/transcribe")
    print("- Text-to-speech: http://localhost:5000/tts")
    print("- Chat messages (hybrid OpenAI + Claude): http://localhost:5000/chat")
    print("- Clear conversation: http://localhost:5000/clear-conversation")
    print("- Generate music (Beatoven.ai): http://localhost:5000/generate-music")
    print("- REAPER actions (Claude-powered): http://localhost:5000/reaper-action")
    print("\nAI Models:")
    print("- OpenAI GPT-3.5-turbo: General chat, music generation detection, TTS")
    print("- Claude Sonnet 4: REAPER DAW operations with advanced tool calling")
    print("- Auto-routing: REAPER requests -> Claude, General chat -> OpenAI")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
