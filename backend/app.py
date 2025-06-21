#!/usr/bin/env python3
"""
Music Production Assistant Backend
Handles LLM processing and REAPER integration using reapy
"""

import json
import sys
import logging
import threading
import time
from datetime import datetime
import random
import os
from typing import Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found. Install with: pip install python-dotenv")

# OpenAI API
try:
    from openai import OpenAI
except ImportError:
    print("Error: openai not found. Please install with: pip install openai")
    OpenAI = None

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

class MusicAssistantBackend:
    def __init__(self):
        self.llm_initialized = False
        self.reaper_connected = False
        self.chat_history = []
        self.track_counter = 1
        
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

def main():
    """Main backend process"""
    backend = MusicAssistantBackend()
    
    logger.info("Music Production Assistant Backend Starting...")
    
    # Initialize components
    backend.initialize_llm()
    backend.connect_to_reaper()
    
    logger.info("Backend ready, listening for messages...")
    
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