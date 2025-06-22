#!/usr/bin/env python3
"""
Music Production Assistant Backend
Handles LLM processing, VAPI integration, and REAPER integration using reapy
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

# VAPI integration
try:
    import requests
except ImportError:
    print("Error: requests not found. Please install with: pip install requests")
    requests = None

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

class VAPIClient:
    """VAPI client for real-time voice processing"""
    
    def __init__(self):
        self.api_key = os.getenv('VAPI_API_KEY')
        self.base_url = "https://api.vapi.ai"
        self.assistant_id = os.getenv('VAPI_ASSISTANT_ID')
        
        if not self.api_key:
            logger.warning("VAPI API key not found in .env file")
        else:
            logger.info("VAPI API key found and configured")
            
        if not self.assistant_id:
            logger.info("VAPI Assistant ID not found - will create temporary assistant")
        else:
            logger.info("VAPI Assistant ID found and configured")
            
    def create_call(self) -> Dict[str, Any]:
        """Create a new VAPI call"""
        if not self.api_key:
            return {"error": "VAPI not configured"}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Build the request data
            data = {
                "assistant": {
                    "model": {
                        "provider": "openai",
                        "model": "gpt-4",
                        "temperature": 0.7,
                        "systemPrompt": "You are a helpful REAPER assistant. You can help users with REAPER workflow questions, audio production advice, track management, effects and processing, automation, MIDI and audio editing. Be helpful, concise, and focus on REAPER-related topics."
                    },
                    "voice": {
                        "provider": "11labs",
                        "voiceId": "pNInz6obpgDQGcFmaJgB"  # Default voice
                    },
                    "firstMessage": "Hi! I'm your REAPER assistant. How can I help you today?"
                }
            }
            
            # Add assistantId if available
            if self.assistant_id:
                data["assistantId"] = self.assistant_id
            
            logger.info(f"Creating VAPI call with data: {data}")
            
            response = requests.post(f"{self.base_url}/call", headers=headers, json=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"VAPI HTTP error: {e}")
            logger.error(f"Response content: {e.response.text if e.response else 'No response'}")
            return {"error": f"VAPI HTTP error: {e}"}
        except Exception as e:
            logger.error(f"Error creating VAPI call: {e}")
            return {"error": str(e)}
    
    def stream_audio(self, call_id: str, audio_chunk: bytes) -> Dict[str, Any]:
        """Stream audio chunk to VAPI"""
        if not self.api_key:
            return {"error": "VAPI not configured"}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "audio/wav"
            }
            
            response = requests.post(
                f"{self.base_url}/call/{call_id}/stream",
                headers=headers,
                data=audio_chunk
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error streaming audio to VAPI: {e}")
            return {"error": str(e)}
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get call status from VAPI"""
        if not self.api_key:
            return {"error": "VAPI not configured"}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            response = requests.get(f"{self.base_url}/call/{call_id}", headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting call status: {e}")
            return {"error": str(e)}

class AudioProcessor:
    """Handle audio processing and buffering"""
    
    def __init__(self):
        self.audio_buffer = []
        self.sample_rate = 16000
        self.channels = 1
        self.sample_width = 2  # 16-bit
        
    def add_audio_chunk(self, audio_data: bytes):
        """Add audio chunk to buffer"""
        self.audio_buffer.append(audio_data)
        
    def get_buffered_audio(self) -> bytes:
        """Get all buffered audio as single chunk"""
        if not self.audio_buffer:
            return b""
        return b"".join(self.audio_buffer)
        
    def clear_buffer(self):
        """Clear audio buffer"""
        self.audio_buffer.clear()
        
    def create_wav_header(self, data_length: int) -> bytes:
        """Create WAV header for audio data"""
        header = bytearray(44)
        
        # RIFF header
        header[0:4] = b'RIFF'
        header[4:8] = (data_length + 36).to_bytes(4, 'little')
        header[8:12] = b'WAVE'
        
        # fmt chunk
        header[12:16] = b'fmt '
        header[16:20] = (16).to_bytes(4, 'little')  # fmt chunk size
        header[20:22] = (1).to_bytes(2, 'little')   # PCM format
        header[22:24] = self.channels.to_bytes(2, 'little')
        header[24:28] = self.sample_rate.to_bytes(4, 'little')
        header[28:32] = (self.sample_rate * self.channels * self.sample_width).to_bytes(4, 'little')  # byte rate
        header[32:34] = (self.channels * self.sample_width).to_bytes(2, 'little')  # block align
        header[34:36] = (self.sample_width * 8).to_bytes(2, 'little')  # bits per sample
        
        # data chunk
        header[36:40] = b'data'
        header[40:44] = data_length.to_bytes(4, 'little')
        
        return bytes(header)
        
    def create_wav_file(self, audio_data: bytes) -> bytes:
        """Create complete WAV file from audio data"""
        header = self.create_wav_header(len(audio_data))
        return header + audio_data

class MusicAssistantBackend:
    def __init__(self):
        self.llm_initialized = False
        self.reaper_connected = False
        self.chat_history = []
        self.track_counter = 1
        
        # VAPI and audio processing
        self.vapi_client = VAPIClient()
        self.audio_processor = AudioProcessor()
        self.active_calls = {}  # Track active VAPI calls
        self.websocket_server = None
        
        # OpenAI configuration
        self.openai_client = None
        self.setup_openai()
        
        # System prompt for the AI
        self.system_prompt = """You are a helpful REAPER assistant. You can help users with:
- REAPER workflow questions
- Audio production advice
- Track management
- Effects and processing
- Automation
- MIDI and audio editing

You can also perform actions in REAPER when users type specific commands:
- Type "track" to create a new track
- Type "melody" to create a track with a C major scale melody

Be helpful, concise, and focus on REAPER-related topics."""
        
    def setup_openai(self):
        """Setup OpenAI client"""
        try:
            # Try to get API key from .env file (loaded by python-dotenv)
            api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                logger.warning("OpenAI API key not found in .env file. Please create a .env file with:")
                logger.warning("OPENAI_API_KEY=your-api-key-here")
                return
            
            if OpenAI and api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI API configured successfully from .env file")
            else:
                logger.warning("OpenAI not available")
                
        except Exception as e:
            logger.error(f"Error setting up OpenAI: {e}")
        
    def initialize_llm(self):
        """Initialize the LLM (OpenAI)"""
        if self.openai_client:
            logger.info("OpenAI LLM initialized successfully")
            self.llm_initialized = True
        else:
            logger.warning("LLM not available - using fallback responses")
            self.llm_initialized = False
        
    def connect_to_reaper(self):
        """Connect to REAPER via reapy"""
        try:
            # Test REAPER connection
            project = reapy.Project()
            logger.info("Successfully connected to REAPER via reapy")
            self.reaper_connected = True
        except Exception as e:
            logger.error(f"Failed to connect to REAPER: {e}")
            self.reaper_connected = False
        
    def create_new_track(self):
        """Create a new track in REAPER using reapy"""
        try:
            if not self.reaper_connected:
                return "Error: Not connected to REAPER"
            
            # Get the current project
            project = reapy.Project()
            
            # Add track with name
            track_name = f"Track {self.track_counter}"
            new_track = project.add_track(name=track_name)
            
            # Increment counter for next track
            self.track_counter += 1
            
            # Return success message
            return f"Successfully created new track: '{track_name}' (ID: {new_track.id})"
            
        except Exception as e:
            return f"Error creating track: {str(e)}"
    
    def create_melody_track(self):
        """Create a track with a C major scale melody"""
        try:
            if not self.reaper_connected:
                return "Error: Not connected to REAPER"
            
            # Get the current project
            project = reapy.Project()
            
            # Add track with name
            track_name = f"Melody Track {self.track_counter}"
            new_track = project.add_track(name=track_name)
            
            # Create a simple melody (C major scale)
            melody_notes = [
                (60, 0, 1),    # C4 - start at 0 seconds, duration 1 second
                (62, 1, 1),    # D4 - start at 1 second, duration 1 second
                (64, 2, 1),    # E4 - start at 2 seconds, duration 1 second
                (65, 3, 1),    # F4 - start at 3 seconds, duration 1 second
                (67, 4, 1),    # G4 - start at 4 seconds, duration 1 second
                (69, 5, 1),    # A4 - start at 5 seconds, duration 1 second
                (71, 6, 1),    # B4 - start at 6 seconds, duration 1 second
                (72, 7, 1),    # C5 - start at 7 seconds, duration 1 second
            ]
            
            # Create a MIDI item on the track
            midi_item = new_track.add_midi_item(start=0, end=8)
            
            # Get the MIDI take
            take = midi_item.takes[0]
            
            # Add notes to the take
            for note_num, start_time, duration in melody_notes:
                take.add_note(
                    start=start_time,
                    end=start_time + duration,
                    pitch=note_num,
                    velocity=100,
                    channel=0
                )
            
            # Add a virtual instrument to the track (ReaSynth - built into REAPER)
            new_track.add_fx(name="ReaSynth")
            
            # Increment counter for next track
            self.track_counter += 1
            
            return f"Successfully created melody track: '{track_name}' with C major scale and ReaSynth"
            
        except Exception as e:
            return f"Error creating melody track: {str(e)}"
    
    def get_ai_response(self, user_message):
        """Get response from OpenAI API"""
        if not self.openai_client:
            return None
        
        try:
            # Prepare messages for OpenAI
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]
            
            # Add conversation history (last 10 messages to stay within limits)
            recent_history = self.chat_history[-10:] if len(self.chat_history) > 10 else self.chat_history
            for msg in recent_history:
                role = "user" if msg["is_user"] else "assistant"
                messages.append({"role": role, "content": msg["text"]})
            
            # Add current user message
            messages.append({"role": "user", "content": user_message})
            
            # Get response from OpenAI using new API
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=150,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return None
        
    def process_message(self, message: str) -> Dict[str, Any]:
        """Process user message and generate response"""
        logger.info(f"Processing message: {message}")
        
        # Add user message to chat history
        self.chat_history.append({"text": message, "is_user": True, "time": datetime.now()})
        
        # Check for special commands
        if message.lower() == "track":
            # Create a new track
            result = self.create_new_track()
            self.chat_history.append({"text": result, "is_user": False, "time": datetime.now()})
            response = {
                "type": "response",
                "content": result,
                "success": True,
                "actions": [{"type": "create_track", "result": result}]
            }
        elif message.lower() == "melody":
            # Create a melody track
            result = self.create_melody_track()
            self.chat_history.append({"text": result, "is_user": False, "time": datetime.now()})
            response = {
                "type": "response",
                "content": result,
                "success": True,
                "actions": [{"type": "create_melody", "result": result}]
            }
        else:
            # Get AI response or fallback
            ai_response = self.get_ai_response(message)
            
            if ai_response:
                response_content = ai_response
            else:
                # Fallback responses
                fallback_responses = [
                    "That's an interesting question! I'm here to help with REAPER-related tasks.",
                    "I understand you're asking about that. Let me think...",
                    "Thanks for your message! I'm here to help with REAPER workflows.",
                    "I'm designed to help with REAPER workflows and audio production questions.",
                    "That's a great point! As a REAPER assistant, I can help with various tasks.",
                    "I can help you with track management, effects, automation, and more!",
                    "Let me know if you need help with any REAPER features or workflows.",
                    "I'm here to make your REAPER experience smoother and more efficient.",
                ]
                response_content = random.choice(fallback_responses)
            
            self.chat_history.append({"text": response_content, "is_user": False, "time": datetime.now()})
            
            response = {
                "type": "response",
                "content": response_content,
                "success": True,
                "actions": []
            }
        
        return response
        
    def process_voice(self, audio_data: bytes) -> Dict[str, Any]:
        """Process voice input and convert to text"""
        # TODO: Add speech-to-text processing
        logger.info("Voice processing placeholder")
        
        return {
            "type": "response",
            "content": "🎤 Voice processing will be implemented soon!",
            "success": True
        }
        
    def execute_reaper_action(self, action: Dict[str, Any]) -> bool:
        """Execute a REAPER action"""
        try:
            action_type = action.get('type')
            
            if action_type == 'create_track':
                result = self.create_new_track()
                logger.info(f"Executed REAPER action: {result}")
                return True
            elif action_type == 'create_melody':
                result = self.create_melody_track()
                logger.info(f"Executed REAPER action: {result}")
                return True
            else:
                logger.warning(f"Unknown REAPER action type: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing REAPER action: {e}")
            return False

    async def start_websocket_server(self, port=8765):
        """Start WebSocket server for real-time audio streaming"""
        try:
            # Create a handler function that matches the expected signature
            async def handler(websocket):
                await self.handle_websocket_connection(websocket, "/")
            
            self.websocket_server = await websockets.serve(handler, "localhost", port)
            logger.info(f"WebSocket server started on port {port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            return False
    
    async def handle_websocket_connection(self, websocket, path):
        """Handle WebSocket connections from frontend"""
        client_id = id(websocket)
        logger.info(f"New WebSocket connection: {client_id}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    if message_type == 'start_call':
                        # VAPI functionality removed - send placeholder response
                        await websocket.send(json.dumps({
                            'type': 'call_error',
                            'error': 'VAPI functionality has been removed'
                        }))
                    
                    elif message_type == 'audio_chunk':
                        # VAPI functionality removed - ignore audio chunks
                        pass
                    
                    elif message_type == 'end_call':
                        # VAPI functionality removed - send placeholder response
                        await websocket.send(json.dumps({
                            'type': 'call_ended',
                            'success': True
                        }))
                    
                    elif message_type == 'text_message':
                        # Handle text message (existing functionality)
                        response = self.process_message(data.get('content', ''))
                        await websocket.send(json.dumps(response))
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from WebSocket: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'error': 'Invalid JSON format'
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            # Clean up if connection is lost
            if client_id in self.active_calls:
                del self.active_calls[client_id]
                self.audio_processor.clear_buffer()

def main():
    """Main backend process"""
    backend = MusicAssistantBackend()
    
    logger.info("Music Production Assistant Backend Starting...")
    
    # Initialize components
    backend.initialize_llm()
    backend.connect_to_reaper()
    
    # Start WebSocket server in a separate thread
    async def run_websocket_server():
        await backend.start_websocket_server()
        await asyncio.Future()  # Keep running
    
    def start_websocket():
        asyncio.run(run_websocket_server())
    
    websocket_thread = threading.Thread(target=start_websocket, daemon=True)
    websocket_thread.start()
    
    logger.info("Backend ready, listening for messages...")
    logger.info("WebSocket server starting on port 8765...")
    
    try:
        while True:
            # Read input from stdin (from Electron)
            line = sys.stdin.readline()
            if not line:
                break
                
            try:
                data = json.loads(line.strip())
                message_type = data.get('type')
                content = data.get('content')
                
                if message_type == 'message':
                    response = backend.process_message(content)
                elif message_type == 'voice':
                    response = backend.process_voice(content)
                else:
                    response = {
                        "type": "error",
                        "content": f"Unknown message type: {message_type}",
                        "success": False
                    }
                    
                # Send response back to Electron
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                error_response = {
                    "type": "error",
                    "content": f"Invalid JSON: {e}",
                    "success": False
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        logger.info("Backend shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 