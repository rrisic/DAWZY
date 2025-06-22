#!/usr/bin/env python3
"""
Music Production Assistant Backend
Handles LLM processing, OpenAI Whisper transcription, and REAPER integration using reapy
"""

import json
import sys
import logging
import base64
import tempfile
import os
import time
import re
from datetime import datetime
from typing import Optional, List

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

# Pydantic for structured data
try:
    from pydantic import BaseModel, Field
except ImportError:
    print("Error: pydantic not found. Please install with: pip install pydantic")
    BaseModel = None

# Requests for Beatoven.ai API
try:
    import requests
except ImportError:
    print("Error: requests not found. Please install with: pip install requests")
    requests = None

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

# Pydantic model for structured music generation
if BaseModel:
    class MusicGenerationRequest(BaseModel):
        """Structured model for Beatoven.ai music generation parameters"""
        genre: Optional[str] = Field(default="electronic", description="Music genre (e.g., electronic, ambient, rock, jazz)")
        tempo: Optional[int] = Field(default=120, description="BPM (beats per minute), typically 60-200")
        mood: Optional[str] = Field(default="energetic", description="Mood/emotion (e.g., happy, sad, energetic, calm, dark)")
        duration: Optional[int] = Field(default=30, description="Duration in seconds, typically 15-120")
        instruments: Optional[List[str]] = Field(default=["drums", "bass", "synth"], description="List of instruments to include")
        key: Optional[str] = Field(default="C major", description="Musical key (e.g., C major, A minor, D major)")
        intensity: Optional[str] = Field(default="medium", description="Intensity level (low, medium, high)")
        style_descriptors: Optional[List[str]] = Field(default=[], description="Additional style descriptors")
        exclude_instruments: Optional[List[str]] = Field(default=[], description="Instruments to specifically exclude")
        
        def to_beatoven_prompt(self) -> str:
            """Convert structured parameters to Beatoven.ai prompt"""
            prompt_parts = []
            
            # Base description
            prompt_parts.append(f"Create a {self.mood} {self.genre} track")
            
            # Tempo
            if self.tempo:
                prompt_parts.append(f"at {self.tempo} BPM")
            
            # Duration
            if self.duration:
                prompt_parts.append(f"lasting {self.duration} seconds")
            
            # Instruments to include
            if self.instruments:
                instruments_str = ", ".join(self.instruments)
                prompt_parts.append(f"featuring {instruments_str}")
            
            # Instruments to exclude
            if self.exclude_instruments:
                exclude_str = ", ".join(self.exclude_instruments)
                prompt_parts.append(f"without {exclude_str}")
            
            # Musical key
            if self.key and self.key != "C major":
                prompt_parts.append(f"in {self.key}")
            
            # Intensity
            if self.intensity != "medium":
                prompt_parts.append(f"with {self.intensity} intensity")
            
            # Additional style descriptors
            if self.style_descriptors:
                style_str = ", ".join(self.style_descriptors)
                prompt_parts.append(f"with {style_str} characteristics")
            
            return ". ".join(prompt_parts) + "."
else:
    # Fallback if Pydantic not available
    class MusicGenerationRequest:
        def __init__(self, **kwargs):
            self.genre = kwargs.get('genre', 'electronic')
            self.tempo = kwargs.get('tempo', 120)
            self.mood = kwargs.get('mood', 'energetic')
            self.duration = kwargs.get('duration', 30)
            self.instruments = kwargs.get('instruments', ['drums', 'bass', 'synth'])
            self.key = kwargs.get('key', 'C major')
            self.intensity = kwargs.get('intensity', 'medium')
            self.style_descriptors = kwargs.get('style_descriptors', [])
            self.exclude_instruments = kwargs.get('exclude_instruments', [])
        
        def dict(self):
            return {
                'genre': self.genre,
                'tempo': self.tempo,
                'mood': self.mood,
                'duration': self.duration,
                'instruments': self.instruments,
                'key': self.key,
                'intensity': self.intensity,
                'style_descriptors': self.style_descriptors,
                'exclude_instruments': self.exclude_instruments
            }
        
        def to_beatoven_prompt(self) -> str:
            """Convert structured parameters to Beatoven.ai prompt"""
            prompt_parts = []
            
            # Base description
            prompt_parts.append(f"Create a {self.mood} {self.genre} track")
            
            # Tempo
            if self.tempo:
                prompt_parts.append(f"at {self.tempo} BPM")
            
            # Duration
            if self.duration:
                prompt_parts.append(f"lasting {self.duration} seconds")
            
            # Instruments to include
            if self.instruments:
                instruments_str = ", ".join(self.instruments)
                prompt_parts.append(f"featuring {instruments_str}")
            
            # Instruments to exclude
            if self.exclude_instruments:
                exclude_str = ", ".join(self.exclude_instruments)
                prompt_parts.append(f"without {exclude_str}")
            
            # Musical key
            if self.key and self.key != "C major":
                prompt_parts.append(f"in {self.key}")
            
            # Intensity
            if self.intensity != "medium":
                prompt_parts.append(f"with {self.intensity} intensity")
            
            # Additional style descriptors
            if self.style_descriptors:
                style_str = ", ".join(self.style_descriptors)
                prompt_parts.append(f"with {style_str} characteristics")
            
            return ". ".join(prompt_parts) + "."

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
        'list tracks', 'show tracks', 'track named', 'track called', 'delete',
        
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
        'automation', 'routing', 'send', 'bus',

        'edit'
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

def detect_music_generation(message: str) -> bool:
    """Detect if a user message is requesting music generation"""
    return "generate" in message.lower()

def parse_music_generation_request(message: str) -> MusicGenerationRequest:
    """Parse user message and extract music generation parameters"""
    message_lower = message.lower()
    
    # Extract genre
    genre_keywords = {
        "electronic": ["electronic", "edm", "techno", "house", "trance"],
        "ambient": ["ambient", "atmospheric", "peaceful", "calm"],
        "rock": ["rock", "metal", "punk", "grunge"],
        "jazz": ["jazz", "swing", "bebop"],
        "classical": ["classical", "orchestral", "piano"],
        "hip hop": ["hip hop", "rap", "beats"],
        "folk": ["folk", "acoustic", "country"],
        "pop": ["pop", "commercial"],
        "funk": ["funk", "groove"],
        "blues": ["blues"],
        "reggae": ["reggae"],
        "drum and bass": ["drum and bass", "dnb", "jungle"]
    }
    
    detected_genre = "electronic"  # default
    for genre, keywords in genre_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_genre = genre
            break
    
    # Extract tempo/BPM
    tempo_match = re.search(r'(\d+)\s*bpm|(\d+)\s*beats|tempo\s*(\d+)', message_lower)
    detected_tempo = 120  # default
    if tempo_match:
        tempo_value = tempo_match.group(1) or tempo_match.group(2) or tempo_match.group(3)
        try:
            parsed_tempo = int(tempo_value)
            if 60 <= parsed_tempo <= 200:
                detected_tempo = parsed_tempo
        except ValueError:
            pass
    
    # Extract mood
    mood_keywords = {
        "happy": ["happy", "joyful", "upbeat", "cheerful", "bright"],
        "sad": ["sad", "melancholy", "emotional", "slow", "depressing"],
        "energetic": ["energetic", "powerful", "intense", "driving", "uplifting"],
        "calm": ["calm", "peaceful", "relaxing", "soothing", "gentle"],
        "dark": ["dark", "heavy", "aggressive", "hard", "brutal"],
        "mysterious": ["mysterious", "eerie", "suspenseful"],
        "romantic": ["romantic", "love", "sensual"],
        "epic": ["epic", "cinematic", "dramatic", "heroic"]
    }
    
    detected_mood = "energetic"  # default
    for mood, keywords in mood_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_mood = mood
            break
    
    # Extract duration
    duration_match = re.search(r'(\d+)\s*seconds?|(\d+)\s*minutes?|(\d+)\s*mins?', message_lower)
    detected_duration = 30  # default
    if duration_match:
        if duration_match.group(1):  # seconds
            try:
                detected_duration = min(int(duration_match.group(1)), 120)
            except ValueError:
                pass
        elif duration_match.group(2) or duration_match.group(3):  # minutes
            try:
                minutes = int(duration_match.group(2) or duration_match.group(3))
                detected_duration = min(minutes * 60, 120)
            except ValueError:
                pass
    
    # Extract instruments
    instrument_keywords = {
        "drums": ["drums", "kick", "snare", "hi-hat", "percussion"],
        "bass": ["bass", "bassline", "sub"],
        "guitar": ["guitar", "electric guitar", "acoustic guitar"],
        "piano": ["piano", "keys", "keyboard"],
        "synth": ["synth", "synthesizer", "lead", "pad"],
        "strings": ["strings", "violin", "orchestra"],
        "brass": ["brass", "trumpet", "saxophone", "horn"],
        "vocals": ["vocals", "voice", "singing"],
        "flute": ["flute", "woodwind"],
        "harp": ["harp"],
        "organ": ["organ"]
    }
    
    detected_instruments = []
    for instrument, keywords in instrument_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            detected_instruments.append(instrument)
    
    # Default instruments if none detected
    if not detected_instruments:
        detected_instruments = ["drums", "bass", "synth"]
    
    # Extract excluded instruments
    excluded_instruments = []
    exclude_patterns = [
        r'without\s+(\w+)',
        r'no\s+(\w+)',
        r'exclude\s+(\w+)',
        r'minus\s+(\w+)'
    ]
    
    for pattern in exclude_patterns:
        matches = re.findall(pattern, message_lower)
        for match in matches:
            for instrument, keywords in instrument_keywords.items():
                if match in keywords:
                    excluded_instruments.append(instrument)
                    if instrument in detected_instruments:
                        detected_instruments.remove(instrument)
    
    # Extract musical key
    key_match = re.search(r'in\s+([A-G](?:#|b)?\s+(?:major|minor))', message_lower)
    detected_key = "C major"  # default
    if key_match:
        detected_key = key_match.group(1).title()
    
    # Extract intensity
    detected_intensity = "medium"  # default
    if any(word in message_lower for word in ["soft", "gentle", "quiet", "subtle"]):
        detected_intensity = "low"
    elif any(word in message_lower for word in ["loud", "intense", "powerful", "heavy", "aggressive"]):
        detected_intensity = "high"
    
    return MusicGenerationRequest(
        genre=detected_genre,
        tempo=detected_tempo,
        mood=detected_mood,
        duration=detected_duration,
        instruments=detected_instruments,
        key=detected_key,
        intensity=detected_intensity,
        exclude_instruments=excluded_instruments
    )

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio using OpenAI Whisper (voice input only)"""
    try:
        data = request.get_json()
        if not data or 'audio' not in data:
            return jsonify({'success': False, 'error': 'No audio data provided'})
        
        # Decode base64 audio
        audio_data = base64.b64decode(data['audio'])
        
        # Create temporary file for transcription processing
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
            
            logger.info(f"Voice transcription successful: {transcript}")
            
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

@app.route('/convert-to-midi', methods=['POST'])
def convert_to_midi():
    """Convert audio to MIDI (record button only)"""
    try:
        data = request.get_json()
        if not data or 'audio' not in data:
            return jsonify({'success': False, 'error': 'No audio data provided'})
        
        # Decode base64 audio
        audio_data = base64.b64decode(data['audio'])
        
        # Save recording as Melody.wav (always overwrites)
        recordings_dir = os.path.join(os.path.dirname(__file__), '..', 'recordings')
        os.makedirs(recordings_dir, exist_ok=True)
        melody_path = os.path.join(recordings_dir, 'Melody.wav')
        
        # Check if file exists and log replacement
        file_exists = os.path.exists(melody_path)
        if file_exists:
            logger.info(f"Replacing existing Melody.wav with new recording")
        else:
            logger.info(f"Creating new Melody.wav recording")
        
        # Save the audio data to Melody.wav (overwrites if exists)
        with open(melody_path, 'wb') as melody_file:
            melody_file.write(audio_data)
        
        logger.info(f"Successfully saved recording as: {melody_path}")
        
        # Process audio to MIDI using ngrok (like hum.py)
        logger.info("Processing audio to MIDI via ngrok...")
        try:
            # Your ngrok URL (from hum.py)
            ngrok_url = 'http://panda-humble-amoeba.ngrok-free.app/transcribe'
            
            # Send the file to ngrok
            with open(melody_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(ngrok_url, files=files)
            
            if response.status_code == 200:
                # Save the response content (MIDI file) to the upload directory
                backend_dir = os.path.dirname(__file__)
                upload_dir = os.path.join(backend_dir, 'upload')
                midi_output_path = os.path.join(upload_dir, 'transcribed.mid')
                with open(midi_output_path, 'wb') as out_file:
                    out_file.write(response.content)
                
                logger.info(f"MIDI file downloaded and saved as: {midi_output_path}")
                
                # Automatically add the MIDI file to the currently selected track in REAPER
                add_media_result = None
                if reaper_controller:
                    try:
                        logger.info("Automatically adding MIDI file to REAPER...")
                        add_media_result = reaper_controller.add_media_file("mid")
                        logger.info(f"Add media result: {add_media_result}")
                    except Exception as e:
                        logger.error(f"Failed to automatically add MIDI to REAPER: {e}")
                        add_media_result = f"Error: {str(e)}"
                
                return jsonify({
                    'success': True,
                    'saved_as': 'Melody.wav',
                    'midi_conversion': {
                        'success': True,
                        'midi_path': midi_output_path,
                        'message': f"MIDI file saved as: {os.path.basename(midi_output_path)}",
                        'reaper_import': add_media_result
                    }
                })
            else:
                logger.error(f"Failed to get MIDI file. Status Code: {response.status_code}, Response: {response.text}")
                return jsonify({
                    'success': False,
                    'error': f"Failed to convert audio to MIDI. Status: {response.status_code}"
                })
                
        except Exception as e:
            logger.error(f"Audio to MIDI conversion error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            })
            
    except Exception as e:
        logger.error(f"MIDI conversion error: {e}")
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
        
        # Check if this is a music generation request first
        if detect_music_generation(message):
            logger.info("Detected music generation request")
            try:
                # Parse and generate music
                music_request = parse_music_generation_request(message)
                logger.info(f"Parsed music parameters: {music_request.dict()}")
                
                result = generate_music_with_beatoven(music_request)
                
                if result['success']:
                    response = f"🎵 Generated music track: {result['filename']}\n\nParameters used:\n- Genre: {music_request.genre}\n- Tempo: {music_request.tempo} BPM\n- Mood: {music_request.mood}\n- Duration: {music_request.duration} seconds\n- Instruments: {', '.join(music_request.instruments)}\n\nThe track has been saved to the generated_music folder!"
                    
                    # Update conversation history
                    conversation_history.append({"role": "user", "content": message})
                    conversation_history.append({"role": "assistant", "content": response})
                    
                    # Keep only the last MAX_HISTORY messages
                    if len(conversation_history) > MAX_HISTORY * 2:
                        conversation_history = conversation_history[-MAX_HISTORY * 2:]
                    
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
                        else:
                            audio_base64 = None
                    except Exception as e:
                        logger.error(f"TTS generation failed: {e}")
                        audio_base64 = None
                    
                    return jsonify({
                        'success': True,
                        'response': response,
                        'audio': audio_base64,
                        'music_generation': result
                    })
                else:
                    response = f"I encountered an error while generating music: {result['error']}"
                    
            except Exception as e:
                logger.error(f"Music generation error: {e}")
                response = f"I encountered an error while generating music: {str(e)}"
        
        # Check if this is a REAPER action request
        elif detect_reaper_action(message) and reaper_controller:
            logger.info("Detected REAPER action request - routing to Claude controller")
            try:
                # Use Claude-powered REAPER controller for DAW operations
                # Pass conversation history for context
                reaper_response = reaper_controller.process_query_with_chaining(message, conversation_history)
                
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
                    'reaper_action': True
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

Be helpful, concise, and focus on practical music production advice. If someone asks about creating tracks, melodies, or specific REAPER features, provide concise,actionable guidance. Keep responses conversational but informative.
DO NOT GIVE LONG MULTI PARAGRAPH EXPLANATIONS. ONLY GIVE CONCISE ANSWERS."""

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

def create_filename_from_request(music_request: MusicGenerationRequest) -> str:
    """Create a filename based on the music generation request"""
    # Create a descriptive filename
    filename_parts = [
        music_request.genre.replace(" ", "_"),
        f"{music_request.tempo}bpm",
        music_request.mood,
        f"{music_request.duration}s"
    ]
    
    # Add timestamp for uniqueness
    timestamp = int(time.time())
    filename_base = "_".join(filename_parts) + f"_{timestamp}"
    
    # Clean filename
    filename_base = re.sub(r'[^a-zA-Z0-9_]', '', filename_base)
    
    return filename_base

def generate_music_with_beatoven(music_request: MusicGenerationRequest) -> dict:
    """Generate music using Beatoven.ai with structured parameters"""
    try:
        if not requests:
            return {'success': False, 'error': 'Requests library not available'}
        
        # Get API key
        api_key = os.getenv('BEATOVEN_AI_API_KEY')
        if not api_key:
            return {'success': False, 'error': 'Beatoven.ai API key not found in environment'}
        
        # Convert Pydantic model to Beatoven.ai prompt
        beatoven_prompt = music_request.to_beatoven_prompt()
        logger.info(f"Generated Beatoven.ai prompt: {beatoven_prompt}")
        
        # Prepare API payload
        payload = {
            "prompt": {
                "text": beatoven_prompt
            },
            "format": "wav",
            "looping": False
        }
        
        # Send request to Beatoven.ai
        response = requests.post(
            "https://public-api.beatoven.ai/api/v1/tracks/compose",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            logger.error(f"Beatoven.ai request failed: {response.status_code} - {response.text}")
            return {'success': False, 'error': f"Beatoven.ai API error: {response.text}"}
        
        response_data = response.json()
        if response_data.get('status') not in ['started', 'composing'] or 'task_id' not in response_data:
            logger.error(f"Invalid Beatoven.ai response: {response_data}")
            return {'success': False, 'error': 'Invalid response from Beatoven.ai'}
        
        task_id = response_data['task_id']
        logger.info(f"Beatoven.ai composition started with task_id: {task_id}")
        
        # Poll for completion
        max_attempts = 60  # 5 minutes with 5-second intervals
        for attempt in range(max_attempts):
            time.sleep(5)
            
            status_response = requests.get(
                f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if status_response.status_code != 200:
                logger.warning(f"Status check failed: {status_response.status_code}")
                continue
            
            status_data = status_response.json()
            status = status_data.get('status')
            
            logger.info(f"Task status: {status} (attempt {attempt + 1}/{max_attempts})")
            
            if status == 'composed':
                # Download the track
                track_url = status_data.get('meta', {}).get('track_url')
                if not track_url:
                    return {'success': False, 'error': 'No track URL in response'}
                
                audio_response = requests.get(track_url)
                if audio_response.status_code != 200:
                    return {'success': False, 'error': 'Failed to download audio file'}
                
                # Save to upload folder as beet.wav (always overwrites)
                upload_dir = os.path.join(os.path.dirname(__file__), 'upload')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Always save as beet.wav
                beet_filepath = os.path.join(upload_dir, 'beet.wav')
                
                # Check if file exists and log replacement
                file_exists = os.path.exists(beet_filepath)
                if file_exists:
                    logger.info(f"Replacing existing beet.wav with new Beatoven.ai generation")
                else:
                    logger.info(f"Creating new beet.wav from Beatoven.ai generation")
                
                with open(beet_filepath, 'wb') as f:
                    f.write(audio_response.content)
                
                logger.info(f"Successfully generated and saved music: {beet_filepath}")
                
                # Automatically add the WAV file to a new track using add_media_file
                try:
                    if reaper_controller:
                        logger.info("Automatically adding generated WAV to REAPER...")
                        
                        # Create a track name based on the music parameters
                        track_name = f"Beatoven_{music_request.genre}_{music_request.mood}"
                        
                        # Add the track first
                        add_track_result = reaper_controller.add_track(track_name)
                        logger.info(f"Add track result: {add_track_result}")
                        
                        # Add the WAV file to the new track
                        add_media_result = reaper_controller.add_media_file("wav", track_name)
                        logger.info(f"Add media result: {add_media_result}")
                        
                        return {
                            'success': True,
                            'filename': 'beet.wav',
                            'filepath': beet_filepath,
                            'prompt': beatoven_prompt,
                            'parameters': music_request.dict(),
                            'reaper_integration': {
                                'track_created': add_track_result,
                                'media_added': add_media_result
                            }
                        }
                    else:
                        logger.warning("REAPER controller not available - WAV saved but not added to REAPER")
                        return {
                            'success': True,
                            'filename': 'beet.wav',
                            'filepath': beet_filepath,
                            'prompt': beatoven_prompt,
                            'parameters': music_request.dict(),
                            'reaper_integration': 'REAPER controller not available'
                        }
                except Exception as e:
                    logger.error(f"Error adding WAV to REAPER: {e}")
                    return {
                        'success': True,
                        'filename': 'beet.wav', 
                        'filepath': beet_filepath,
                        'prompt': beatoven_prompt,
                        'parameters': music_request.dict(),
                        'reaper_integration': f'Error adding to REAPER: {str(e)}'
                    }
            
            elif status in ['failed', 'error']:
                return {'success': False, 'error': f'Beatoven.ai composition failed: {status_data}'}
        
        # Timeout
        return {'success': False, 'error': 'Beatoven.ai composition timed out'}
        
    except Exception as e:
        logger.error(f"Music generation error: {e}")
        return {'success': False, 'error': str(e)}

@app.route('/generate-music', methods=['POST'])
def generate_music():
    """Generate music using Beatoven.ai with Pydantic model"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'success': False, 'error': 'No query provided'})
        
        user_query = data['query']
        logger.info(f"Music generation request: {user_query}")
        
        # Parse query into structured parameters
        music_request = parse_music_generation_request(user_query)
        logger.info(f"Parsed parameters: {music_request.dict()}")
        
        # Generate music
        result = generate_music_with_beatoven(music_request)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Generate music endpoint error: {e}")
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
            # Pass conversation history for context in standalone actions too
            result = reaper_controller.process_query_with_chaining(action, conversation_history)
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

if __name__ == "__main__":
    print("Starting Music Production Assistant Backend...")
    print("Available services:")
    print("- OpenAI Whisper transcription: http://localhost:5000/transcribe")
    print("- Text-to-speech: http://localhost:5000/tts")
    print("- Chat messages (hybrid OpenAI + Claude + Beatoven.ai): http://localhost:5000/chat")
    print("- Clear conversation: http://localhost:5000/clear-conversation")
    print("- REAPER actions (Claude-powered): http://localhost:5000/reaper-action")
    print("- Music generation (Beatoven.ai): http://localhost:5000/generate-music")
    print("\nAI Models:")
    print("- OpenAI GPT-3.5-turbo: General chat and TTS")
    print("- Claude Sonnet 4: REAPER DAW operations with advanced tool calling")
    print("- Beatoven.ai: AI music generation with Pydantic structured parameters")
    print("- Auto-routing: 'generate' -> Beatoven.ai, REAPER -> Claude, General -> OpenAI")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
