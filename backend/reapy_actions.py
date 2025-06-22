#!/usr/bin/env python3
"""
REAPER Control with Claude API Tool Calls
Handles track management and FX operations using reapy
"""

import json
import logging
import os
from typing import Dict, Any, List
import reapy

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not found. Install with: pip install python-dotenv")

# Anthropic Claude API
try:
    import anthropic
except ImportError:
    print("Error: anthropic not found. Please install with: pip install anthropic")
    anthropic = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global project instance - hardcoded as requested
try:
    project = reapy.Project()
    logger.info("Connected to REAPER project")
except Exception as e:
    logger.error(f"Failed to connect to REAPER: {e}")
    project = None

class ReaperController:
    def __init__(self):
        self.track_counter = 1
        self.client = None
        self.setup_claude()
        
        # Define tools for Claude
        self.tools = [
            {
                "name": "add_track",
                "description": "Add a new track to REAPER project",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_name": {
                            "type": "string",
                            "description": "Name for the new track"
                        }
                    },
                    "required": ["track_name"]
                }
            },
            {
                "name": "delete_track",
                "description": "Delete a track from REAPER project",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index to delete"
                        }
                    },
                    "required": ["track_identifier"]
                }
            },
            {
                "name": "add_fx_to_track",
                "description": "Add an FX plugin to a track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "fx_name": {
                            "type": "string",
                            "description": "Name of the FX plugin to add (e.g., 'ReaSynth', 'ReaEQ', 'ReaComp')"
                        }
                    },
                    "required": ["track_identifier", "fx_name"]
                }
            },
            {
                "name": "remove_fx_from_track",
                "description": "Remove an FX plugin from a track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "fx_index": {
                            "type": "integer",
                            "description": "Index of the FX to remove (0-based)"
                        }
                    },
                    "required": ["track_identifier", "fx_index"]
                }
            },
            {
                "name": "list_tracks",
                "description": "List all tracks in the project",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_fx_on_track",
                "description": "List all FX plugins on a specific track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        }
                    },
                    "required": ["track_identifier"]
                }
            },
            {
                "name": "inspect_fx_parameters",
                "description": "Inspect all parameters of a specific FX on a track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "fx_index": {
                            "type": "integer",
                            "description": "Index of the FX to inspect (0-based)"
                        }
                    },
                    "required": ["track_identifier", "fx_index"]
                }
            },
            {
                "name": "set_fx_parameter",
                "description": "Set a specific parameter value for an FX. IMPORTANT: Always inspect FX parameters first to find the correct parameter index before setting values.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "fx_index": {
                            "type": "integer",
                            "description": "Index of the FX (0-based)"
                        },
                        "param_index": {
                            "type": "integer",
                            "description": "Index of the parameter (0-based) - use inspect_fx_parameters first to find the correct index"
                        },
                        "value": {
                            "type": "number",
                            "description": "Parameter value - can be either raw parameter value (0.0-1.0) OR human-readable formatted value (e.g., 3000 for 3000ms)"
                        },
                        "use_formatted": {
                            "type": "boolean",
                            "description": "If true, treat 'value' as a formatted/human-readable value that needs conversion to parameter range. If false, use raw parameter value.",
                            "default": True
                        }
                    },
                    "required": ["track_identifier", "fx_index", "param_index", "value"]
                }
            },
            {
                "name": "modify_fx_parameter",
                "description": "Modify an FX parameter by multiplying current value or setting absolute value. IMPORTANT: Always inspect FX parameters first to find the correct parameter index.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "fx_index": {
                            "type": "integer",
                            "description": "Index of the FX (0-based)"
                        },
                        "param_index": {
                            "type": "integer",
                            "description": "Index of the parameter (0-based)"
                        },
                        "operation": {
                            "type": "string",
                            "enum": ["multiply", "set"],
                            "description": "Operation to perform: 'multiply' to multiply current value, 'set' to set absolute value"
                        },
                        "value": {
                            "type": "number",
                            "description": "For 'multiply': factor to multiply by (e.g., 1.5). For 'set': absolute value to set (0.0 to 1.0)"
                        }
                    },
                    "required": ["track_identifier", "fx_index", "param_index", "operation", "value"]
                }
            },
            {
                "name": "add_midi_item",
                "description": "Add a MIDI item to a track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "start_time": {
                            "type": "number",
                            "description": "Start time of the MIDI item in seconds",
                            "default": 0
                        },
                        "end_time": {
                            "type": "number",
                            "description": "End time of the MIDI item in seconds",
                            "default": 4
                        }
                    },
                    "required": ["track_identifier"]
                }
            },
            {
                "name": "add_note_to_track",
                "description": "Add a MIDI note to the active MIDI item on a track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "start_time": {
                            "type": "number",
                            "description": "Note start time in seconds"
                        },
                        "end_time": {
                            "type": "number",
                            "description": "Note end time in seconds"
                        },
                        "pitch": {
                            "type": "integer",
                            "description": "MIDI pitch (0-127, where 60 = C4)"
                        },
                        "velocity": {
                            "type": "integer",
                            "description": "Note velocity (0-127)",
                            "default": 100
                        },
                        "channel": {
                            "type": "integer",
                            "description": "MIDI channel (0-15)",
                            "default": 0
                        }
                    },
                    "required": ["track_identifier", "start_time", "end_time", "pitch"]
                }
            },
            {
                "name": "list_notes_on_track",
                "description": "List all MIDI notes on a track",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "item_index": {
                            "type": "integer",
                            "description": "Index of the MIDI item (0-based). If not specified, uses the first MIDI item",
                            "default": 0
                        }
                    },
                    "required": ["track_identifier"]
                }
            },
            {
                "name": "transpose_notes",
                "description": "Transpose all notes on a track by a specified number of semitones",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "semitones": {
                            "type": "integer",
                            "description": "Number of semitones to transpose (positive = up, negative = down, 12 = one octave)"
                        },
                        "item_index": {
                            "type": "integer",
                            "description": "Index of the MIDI item (0-based). If not specified, transposes all MIDI items",
                            "default": -1
                        }
                    },
                    "required": ["track_identifier", "semitones"]
                }
            },
            {
                "name": "add_multiple_notes",
                "description": "Add multiple MIDI notes to a track at once. Use this to add several notes in one operation.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "track_identifier": {
                            "type": "string",
                            "description": "Track name or index"
                        },
                        "note_data": {
                            "type": "string",
                            "description": "Comma-separated note data in format: 'pitch,start,end,velocity|pitch,start,end,velocity|...' where pitch=0-127, start/end=seconds, velocity=0-127 (optional, default 100). Example: '60,0,1,100|64,1,2,100|67,2,3,100' for C4, E4, G4 notes"
                        }
                    },
                    "required": ["track_identifier", "note_data"]
                }
            }
            
        ]
    
    def setup_claude(self):
        """Setup Claude API client"""
        try:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                logger.warning("Anthropic API key not found in .env file. Please add:")
                logger.warning("ANTHROPIC_API_KEY=your-api-key-here")
                return
            
            if anthropic and api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
                logger.info("Claude API configured successfully")
            else:
                logger.warning("Claude API not available")
        except Exception as e:
            logger.error(f"Error setting up Claude API: {e}")
    
    def add_track(self, track_name: str) -> str:
        """Add a new track to REAPER"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            new_track = project.add_track(name=track_name)
            logger.info(f"Created track: {track_name}")
            return f"Successfully created track: '{track_name}'"
        except Exception as e:
            return f"Error creating track: {str(e)}"
    
    def delete_track(self, track_identifier: str) -> str:
        """Delete a track from REAPER"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Try to find track by name first, then by index
            track = None
            
            # Search by name
            for t in project.tracks:
                if t.name == track_identifier:
                    track = t
                    break
            
            # If not found by name, try by index
            if not track:
                try:
                    track_index = int(track_identifier)
                    if 0 <= track_index < len(project.tracks):
                        track = project.tracks[track_index]
                except ValueError:
                    pass
            
            if not track:
                return f"Track '{track_identifier}' not found"
            
            track_name = track.name
            track.delete()
            logger.info(f"Deleted track: {track_name}")
            return f"Successfully deleted track: '{track_name}'"
            
        except Exception as e:
            return f"Error deleting track: {str(e)}"
    
    def add_fx_to_track(self, track_identifier: str, fx_name: str) -> str:
        """Add FX to a track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Add FX
            fx = track.add_fx(name=fx_name)
            logger.info(f"Added FX '{fx_name}' to track '{track.name}'")
            return f"Successfully added '{fx_name}' to track '{track.name}'"
            
        except Exception as e:
            return f"Error adding FX: {str(e)}"
    
    def remove_fx_from_track(self, track_identifier: str, fx_index: int) -> str:
        """Remove FX from a track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Check if FX index is valid
            if fx_index < 0 or fx_index >= len(track.fxs):
                return f"FX index {fx_index} is out of range (0-{len(track.fxs)-1})"
            
            # Remove FX
            fx = track.fxs[fx_index]
            fx_name = fx.name if hasattr(fx, 'name') else f"FX {fx_index}"
            fx.delete()
            logger.info(f"Removed FX '{fx_name}' from track '{track.name}'")
            return f"Successfully removed FX at index {fx_index} from track '{track.name}'"
            
        except Exception as e:
            return f"Error removing FX: {str(e)}"
    
    def list_tracks(self) -> str:
        """List all tracks in the project"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            if not project.tracks:
                return "No tracks found in project"
            
            track_list = []
            for i, track in enumerate(project.tracks):
                fx_count = len(track.fxs)
                track_info = f"{i}: '{track.name}' ({fx_count} FX)"
                track_list.append(track_info)
            
            return "Tracks in project:\n" + "\n".join(track_list)
            
        except Exception as e:
            return f"Error listing tracks: {str(e)}"
    
    def list_fx_on_track(self, track_identifier: str) -> str:
        """List all FX plugins on a specific track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            if not track.fxs:
                return f"No FX found on track '{track.name}'"
            
            fx_list = []
            fx_list.append(f"FX on track '{track.name}':")
            fx_list.append("-" * 40)
            
            for i, fx in enumerate(track.fxs):
                param_count = len(fx.params) if hasattr(fx, 'params') else 0
                fx_info = f"{i}: {fx.name} ({param_count} parameters)"
                fx_list.append(fx_info)
            
            return "\n".join(fx_list)
            
        except Exception as e:
            return f"Error listing FX: {str(e)}"
    
    def inspect_fx_parameters(self, track_identifier: str, fx_index: int) -> str:
        """Inspect all parameters of a specific FX on a track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Check if FX index is valid
            if fx_index < 0 or fx_index >= len(track.fxs):
                return f"FX index {fx_index} is out of range (0-{len(track.fxs)-1})"
            
            fx = track.fxs[fx_index]
            
            # Build detailed parameter information
            result = []
            result.append(f"FX: {fx.name}")
            result.append(f"Track: {track.name}")
            result.append(f"Number of parameters: {len(fx.params)}")
            result.append("-" * 50)
            
            for i, param in enumerate(fx.params):
                param_info = [f"Param {i}: {param.name} = {param:.3f}"]
                
                # Try to get formatted value if supported
                try:
                    formatted_value = param.formatted
                    param_info.append(f"  Formatted: {formatted_value}")
                except:
                    param_info.append(f"  Formatted: Not available")
                
                # Try to get normalized value
                try:
                    normalized_value = param.normalized
                    param_info.append(f"  Normalized: {normalized_value:.3f}")
                except:
                    param_info.append(f"  Normalized: Not available")
                
                # Try to get min/max values
                try:
                    min_val = param.min
                    max_val = param.max
                    param_info.append(f"  Range: {min_val:.3f} to {max_val:.3f}")
                except:
                    param_info.append(f"  Range: Not available")
                
                result.extend(param_info)
                result.append("")  # Empty line for readability
            
            return "\n".join(result)
            
        except Exception as e:
            return f"Error inspecting FX parameters: {str(e)}"
    
    def set_fx_parameter(self, track_identifier: str, fx_index: int, param_index: int, value: float, use_formatted: bool = True) -> str:
        """Set a specific parameter value for an FX"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Check if FX index is valid
            if fx_index < 0 or fx_index >= len(track.fxs):
                return f"FX index {fx_index} is out of range (0-{len(track.fxs)-1})"
            
            fx = track.fxs[fx_index]
            logger.info(f"Found FX: {fx.name}, type: {type(fx)}")
            
            # Check if parameter index is valid
            if param_index < 0 or param_index >= len(fx.params):
                return f"Parameter index {param_index} is out of range (0-{len(fx.params)-1})"
            
            param = fx.params[param_index]
            logger.info(f"Found param: {param.name}, type: {type(param)}")
            
            old_value = float(param)
            logger.info(f"Got old value: {old_value}")
            
            # Convert formatted value to parameter value if needed
            if use_formatted:
                converted_value = self._convert_formatted_to_param_value(param, value)
                logger.info(f"Converted formatted value {value} to parameter value {converted_value}")
                actual_value_to_set = converted_value
            else:
                actual_value_to_set = value
            
            logger.info(f"Setting parameter value to: {actual_value_to_set}")
            
            # Set parameter directly using fx.params[index] = value (this works!)
            fx.params[param_index] = actual_value_to_set
            logger.info("Successfully set parameter using fx.params[index] assignment")
            
            new_value = float(param)
            logger.info(f"Got new value: {new_value}")
            
            logger.info(f"Set {fx.name} param {param_index} ({param.name}) from {old_value:.3f} to {new_value:.3f}")
            
            # Show both formatted and actual values in response
            try:
                new_formatted = param.formatted
                if use_formatted:
                    return f"Successfully set parameter '{param.name}' on '{fx.name}' to {new_formatted} (target: {value}, actual param: {new_value:.3f})"
                else:
                    return f"Successfully set parameter '{param.name}' on '{fx.name}' to {new_value:.3f} (formatted: {new_formatted})"
            except:
                return f"Successfully set parameter '{param.name}' on '{fx.name}' to {new_value:.3f}"
            
        except Exception as e:
            logger.error(f"Error in set_fx_parameter: {e}")
            logger.error(f"Track: {track_identifier}, FX: {fx_index}, Param: {param_index}, Value: {value}")
            return f"Error setting FX parameter: {str(e)}"
    
    def modify_fx_parameter(self, track_identifier: str, fx_index: int, param_index: int, operation: str, value: float) -> str:
        """Modify an FX parameter by multiplying current value or setting absolute value"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Check if FX index is valid
            if fx_index < 0 or fx_index >= len(track.fxs):
                return f"FX index {fx_index} is out of range (0-{len(track.fxs)-1})"
            
            fx = track.fxs[fx_index]
            logger.info(f"Modify FX: {fx.name}, type: {type(fx)}")
            
            # Check if parameter index is valid
            if param_index < 0 or param_index >= len(fx.params):
                return f"Parameter index {param_index} is out of range (0-{len(fx.params)-1})"
            
            param = fx.params[param_index]
            logger.info(f"Modify param: {param.name}, type: {type(param)}")
            
            current_value = float(param)
            logger.info(f"Current value: {current_value}")
            
            if operation == "multiply":
                # Multiply current value by the factor
                new_value = current_value * value
                logger.info(f"Calculated new value: {new_value}")
                
                # Set parameter directly using fx.params[index] = value
                fx.params[param_index] = new_value
                logger.info("Successfully set parameter using fx.params[index] assignment")
                
                actual_new_value = float(param)
                
                logger.info(f"Multiplied {fx.name} param {param_index} ({param.name}) by {value:.3f}: {current_value:.3f} -> {actual_new_value:.3f}")
                return f"Successfully multiplied parameter '{param.name}' on '{fx.name}' by {value:.3f} (new value: {actual_new_value:.3f})"
                
            elif operation == "set":
                # Set parameter directly using fx.params[index] = value
                fx.params[param_index] = value
                logger.info("Successfully set parameter using fx.params[index] assignment")
                
                actual_new_value = float(param)
                 
                logger.info(f"Set {fx.name} param {param_index} ({param.name}) from {current_value:.3f} to {actual_new_value:.3f}")
                return f"Successfully set parameter '{param.name}' on '{fx.name}' to {value:.3f}"
                
            else:
                return f"Invalid operation '{operation}'. Use 'multiply' or 'set'"
            
        except Exception as e:
            logger.error(f"Error in modify_fx_parameter: {e}")
            logger.error(f"Track: {track_identifier}, FX: {fx_index}, Param: {param_index}, Operation: {operation}, Value: {value}")
            return f"Error modifying FX parameter: {str(e)}"
    
    def add_midi_item(self, track_identifier: str, start_time: float = 0, end_time: float = 4) -> str:
        """Add a MIDI item to a track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Add MIDI item
            midi_item = track.add_midi_item(start=start_time, end=end_time)
            logger.info(f"Added MIDI item to track '{track.name}' from {start_time}s to {end_time}s")
            return f"Successfully added MIDI item to track '{track.name}' from {start_time}s to {end_time}s"
            
        except Exception as e:
            return f"Error adding MIDI item: {str(e)}"
    
    def add_note_to_track(self, track_identifier: str, start_time: float, end_time: float, 
                         pitch: int, velocity: int = 100, channel: int = 0) -> str:
        """Add a MIDI note to the active MIDI item on a track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Find MIDI items on track
            midi_items = [item for item in track.items if item.active_take and item.active_take.is_midi]
            if not midi_items:
                return f"No MIDI items found on track '{track.name}'. Create a MIDI item first."
            
            # Use the first MIDI item (or you could specify which one)
            midi_item = midi_items[0]
            take = midi_item.active_take
            
            # Validate pitch range
            if not (0 <= pitch <= 127):
                return f"Invalid pitch {pitch}. Must be between 0 and 127."
            
            # Validate velocity range
            if not (0 <= velocity <= 127):
                return f"Invalid velocity {velocity}. Must be between 0 and 127."
            
            # Validate channel range
            if not (0 <= channel <= 15):
                return f"Invalid channel {channel}. Must be between 0 and 15."
            
            # Add note
            take.add_note(
                start=start_time,
                end=end_time,
                pitch=pitch,
                velocity=velocity,
                channel=channel
            )
            
            # Convert pitch to note name for display
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = (pitch // 12) - 1
            note_name = note_names[pitch % 12] + str(octave)
            
            logger.info(f"Added note {note_name} (pitch {pitch}) to track '{track.name}'")
            return f"Successfully added note {note_name} (pitch {pitch}) to track '{track.name}' from {start_time}s to {end_time}s"
            
        except Exception as e:
            return f"Error adding note: {str(e)}"
    
    def list_notes_on_track(self, track_identifier: str, item_index: int = 0) -> str:
        """List all MIDI notes on a track"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Find MIDI items on track
            midi_items = [item for item in track.items if item.active_take and item.active_take.is_midi]
            if not midi_items:
                return f"No MIDI items found on track '{track.name}'"
            
            if item_index >= len(midi_items):
                return f"MIDI item index {item_index} out of range. Track has {len(midi_items)} MIDI items."
            
            midi_item = midi_items[item_index]
            take = midi_item.active_take
            
            if not take.notes:
                return f"No notes found in MIDI item {item_index} on track '{track.name}'"
            
            # Convert pitch to note name helper
            def pitch_to_note_name(pitch):
                note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                octave = (pitch // 12) - 1
                return note_names[pitch % 12] + str(octave)
            
            # List all notes
            note_list = []
            for i, note in enumerate(take.notes):
                note_name = pitch_to_note_name(note.pitch)
                note_info = f"{i}: {note_name} (pitch {note.pitch}) - {note.start:.2f}s to {note.end:.2f}s, vel {note.velocity}, ch {note.channel}"
                note_list.append(note_info)
            
            result = f"Notes in MIDI item {item_index} on track '{track.name}':\n"
            result += "\n".join(note_list)
            return result
            
        except Exception as e:
            return f"Error listing notes: {str(e)}"
    
    def transpose_notes(self, track_identifier: str, semitones: int, item_index: int = -1) -> str:
        """Transpose all notes on a track by specified semitones"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Find MIDI items on track
            midi_items = [item for item in track.items if item.active_take and item.active_take.is_midi]
            if not midi_items:
                return f"No MIDI items found on track '{track.name}'"
            
            # Determine which items to transpose
            items_to_process = []
            if item_index == -1:
                items_to_process = midi_items
                item_desc = "all MIDI items"
            else:
                if item_index >= len(midi_items):
                    return f"MIDI item index {item_index} out of range. Track has {len(midi_items)} MIDI items."
                items_to_process = [midi_items[item_index]]
                item_desc = f"MIDI item {item_index}"
            
            total_notes_transposed = 0
            
            for midi_item in items_to_process:
                take = midi_item.active_take
                
                # Collect all note data before deleting
                notes_data = []
                for note in take.notes:
                    # Get note information using the infos property for efficiency
                    note_info = note.infos
                    notes_data.append({
                        'start': note_info['start'],
                        'end': note_info['end'],
                        'pitch': note_info['pitch'],
                        'velocity': note_info['velocity'],
                        'channel': note_info['channel'],
                        'selected': note_info['selected'],
                        'muted': note_info['muted']
                    })
                
                # Clear all existing notes
                # We need to delete notes in reverse order to avoid index shifting issues
                for i in range(len(take.notes) - 1, -1, -1):
                    take.notes[i].delete()
                
                # Add new notes with transposed pitch
                for note_data in notes_data:
                    new_pitch = note_data['pitch'] + semitones
                    
                    # Clamp to valid MIDI range (0-127)
                    if new_pitch < 0:
                        new_pitch = 0
                    elif new_pitch > 127:
                        new_pitch = 127
                    
                    # Add the transposed note
                    take.add_note(
                        start=note_data['start'],
                        end=note_data['end'],
                        pitch=new_pitch,
                        velocity=note_data['velocity'],
                        channel=note_data['channel'],
                        selected=note_data['selected'],
                        muted=note_data['muted'],
                        sort=False  # Don't sort after each note for efficiency
                    )
                    total_notes_transposed += 1
                
                # Sort all notes at the end for efficiency
                if notes_data:
                    take.sort_events()
            
            # Describe the transposition
            if semitones > 0:
                direction = f"up {semitones} semitones"
                if semitones == 12:
                    direction = "up one octave"
                elif semitones % 12 == 0:
                    direction = f"up {semitones // 12} octaves"
            elif semitones < 0:
                direction = f"down {abs(semitones)} semitones"
                if semitones == -12:
                    direction = "down one octave"
                elif semitones % 12 == 0:
                    direction = f"down {abs(semitones) // 12} octaves"
            else:
                direction = "by 0 semitones (no change)"
            
            logger.info(f"Transposed {total_notes_transposed} notes {direction} on track '{track.name}'")
            return f"Successfully transposed {total_notes_transposed} notes {direction} in {item_desc} on track '{track.name}'"
            
        except Exception as e:
            return f"Error transposing notes: {str(e)}"
    
    def add_multiple_notes(self, track_identifier: str, note_data: str) -> str:
        """Add multiple MIDI notes to a track at once using string format"""
        if not project:
            return "Error: Not connected to REAPER"
        
        try:
            # Debug logging
            logger.info(f"add_multiple_notes: track='{track_identifier}', note_data='{note_data}'")
            
            # Parse note data string
            # Format: "pitch,start,end,velocity|pitch,start,end,velocity|..."
            # Example: "60,0,1,100|64,1,2,100|67,2,3,100"
            
            if not note_data or not note_data.strip():
                return "Error: note_data is empty"
            
            # Find track
            track = self._find_track(track_identifier)
            if not track:
                return f"Track '{track_identifier}' not found"
            
            # Find MIDI items on track
            midi_items = [item for item in track.items if item.active_take and item.active_take.is_midi]
            if not midi_items:
                return f"No MIDI items found on track '{track.name}'. Create a MIDI item first."
            
            # Use the first MIDI item
            midi_item = midi_items[0]
            take = midi_item.active_take
            
            # Parse notes from string
            note_strings = note_data.split('|')
            added_notes = []
            
            for i, note_str in enumerate(note_strings):
                try:
                    note_str = note_str.strip()
                    if not note_str:
                        continue
                        
                    # Split by comma: pitch,start,end,velocity (velocity optional)
                    parts = note_str.split(',')
                    
                    if len(parts) < 3:
                        return f"Invalid note format in note {i}: '{note_str}'. Expected format: 'pitch,start,end' or 'pitch,start,end,velocity'"
                    
                    # Parse components
                    pitch = int(parts[0])
                    start_time = float(parts[1])
                    end_time = float(parts[2])
                    velocity = int(parts[3]) if len(parts) > 3 else 100
                    channel = 0  # Default channel
                    
                    # Validate ranges
                    if not (0 <= pitch <= 127):
                        return f"Invalid pitch {pitch} in note {i}. Must be between 0 and 127."
                    if not (0 <= velocity <= 127):
                        return f"Invalid velocity {velocity} in note {i}. Must be between 0 and 127."
                    if end_time <= start_time:
                        return f"Invalid timing in note {i}: end_time ({end_time}) must be greater than start_time ({start_time})."
                    
                    # Add note (with sort=False for efficiency)
                    take.add_note(
                        start=start_time,
                        end=end_time,
                        pitch=pitch,
                        velocity=velocity,
                        channel=channel,
                        sort=False
                    )
                    
                    # Convert pitch to note name for logging
                    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                    octave = (pitch // 12) - 1
                    note_name = note_names[pitch % 12] + str(octave)
                    
                    added_notes.append(f"{note_name} ({pitch})")
                    
                except ValueError as e:
                    return f"Invalid number format in note {i}: '{note_str}'. Error: {e}"
                except Exception as e:
                    return f"Error processing note {i}: '{note_str}'. Error: {e}"
            
            if not added_notes:
                return "No valid notes were parsed from the note_data"
            
            # Sort all notes at the end for efficiency
            take.sort_events()
            
            logger.info(f"Added {len(added_notes)} notes to track '{track.name}'")
            return f"Successfully added {len(added_notes)} notes to track '{track.name}': {', '.join(added_notes)}"
            
        except Exception as e:
            return f"Error adding multiple notes: {str(e)}"
    
    def _convert_formatted_to_param_value(self, param, target_formatted_value: float) -> float:
        """Convert a formatted value (like 3000ms) to the actual parameter value (like 0.2)"""
        try:
            # Get current parameter value and its formatted representation
            current_param_value = float(param)
            current_formatted_value = float(param.formatted)
            
            logger.info(f"Current: param={current_param_value:.6f}, formatted={current_formatted_value}")
            
            # Calculate the ratio/scaling factor
            if current_formatted_value != 0:
                # Linear scaling: new_param = current_param * (target_formatted / current_formatted)
                scaling_factor = target_formatted_value / current_formatted_value
                new_param_value = current_param_value * scaling_factor
                
                # Clamp to reasonable range (0.0 to 1.0 for most parameters)
                new_param_value = max(0.0, min(1.0, new_param_value))
                
                logger.info(f"Scaling factor: {scaling_factor:.6f}, new param value: {new_param_value:.6f}")
                return new_param_value
            else:
                # If current formatted is 0, we need to find the relationship differently
                # Try setting a test value to understand the scaling
                return self._find_param_value_by_testing(param, target_formatted_value)
                
        except Exception as e:
            logger.error(f"Error converting formatted value: {e}")
            # Fallback: assume direct mapping
            return target_formatted_value / 1000.0  # Common case: ms to 0-1 range
    
    def _find_param_value_by_testing(self, param, target_formatted_value: float) -> float:
        """Find parameter value by testing different values to match formatted output"""
        try:
            original_value = float(param)
            
            # Test a few values to understand the relationship
            test_values = [0.1, 0.2, 0.5, 0.8]
            best_match = 0.1
            best_diff = float('inf')
            
            for test_val in test_values:
                # Temporarily set the parameter
                param.parent_fx.params[param.index] = test_val
                test_formatted = float(param.formatted)
                
                # Calculate how close this is to our target
                diff = abs(test_formatted - target_formatted_value)
                if diff < best_diff:
                    best_diff = diff
                    best_match = test_val
            
            # Restore original value
            param.parent_fx.params[param.index] = original_value
            
            # Use linear interpolation to get closer
            if best_diff > 0:
                # Try to interpolate for better accuracy
                param.parent_fx.params[param.index] = best_match
                current_formatted = float(param.formatted)
                if current_formatted != 0:
                    refined_value = best_match * (target_formatted_value / current_formatted)
                    refined_value = max(0.0, min(1.0, refined_value))
                    param.parent_fx.params[param.index] = original_value  # Restore
                    return refined_value
            
            param.parent_fx.params[param.index] = original_value  # Restore
            return best_match
            
        except Exception as e:
            logger.error(f"Error in testing method: {e}")
            return target_formatted_value / 1000.0  # Fallback
    
    def _find_track(self, track_identifier: str):
        """Helper method to find track by name or index"""
        # Search by name first
        for track in project.tracks:
            if track.name == track_identifier:
                return track
        
        # Try by index
        try:
            track_index = int(track_identifier)
            if 0 <= track_index < len(project.tracks):
                return project.tracks[track_index]
        except ValueError:
            pass
        
        return None
    
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool function"""
        try:
            logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")
            
            if tool_name == "add_track":
                return self.add_track(arguments["track_name"])
            elif tool_name == "delete_track":
                return self.delete_track(arguments["track_identifier"])
            elif tool_name == "add_fx_to_track":
                return self.add_fx_to_track(arguments["track_identifier"], arguments["fx_name"])
            elif tool_name == "remove_fx_from_track":
                return self.remove_fx_from_track(arguments["track_identifier"], arguments["fx_index"])
            elif tool_name == "list_tracks":
                return self.list_tracks()
            elif tool_name == "list_fx_on_track":
                return self.list_fx_on_track(arguments["track_identifier"])
            elif tool_name == "inspect_fx_parameters":
                return self.inspect_fx_parameters(arguments["track_identifier"], arguments["fx_index"])
            elif tool_name == "set_fx_parameter":
                return self.set_fx_parameter(
                    arguments["track_identifier"], 
                    arguments["fx_index"], 
                    arguments["param_index"], 
                    arguments["value"],
                    arguments.get("use_formatted", True)
                )
            elif tool_name == "modify_fx_parameter":
                return self.modify_fx_parameter(
                    arguments["track_identifier"], 
                    arguments["fx_index"], 
                    arguments["param_index"], 
                    arguments["operation"],
                    arguments["value"]
                )
            elif tool_name == "add_midi_item":
                return self.add_midi_item(
                    arguments["track_identifier"],
                    arguments.get("start_time", 0),
                    arguments.get("end_time", 4)
                )
            elif tool_name == "add_note_to_track":
                return self.add_note_to_track(
                    arguments["track_identifier"],
                    arguments["start_time"],
                    arguments["end_time"],
                    arguments["pitch"],
                    arguments.get("velocity", 100),
                    arguments.get("channel", 0)
                )
            elif tool_name == "list_notes_on_track":
                return self.list_notes_on_track(
                    arguments["track_identifier"],
                    arguments.get("item_index", 0)
                )
            elif tool_name == "transpose_notes":
                return self.transpose_notes(
                    arguments["track_identifier"],
                    arguments["semitones"],
                    arguments.get("item_index", -1)
                )
            elif tool_name == "add_multiple_notes":
                # Debug logging to see what arguments we received
                logger.info(f"add_multiple_notes called with arguments: {arguments}")
                
                # Check if required parameters exist
                if "track_identifier" not in arguments:
                    return "Error: Missing required parameter 'track_identifier'"
                if "note_data" not in arguments:
                    return f"Error: Missing required parameter 'note_data'. Received arguments: {list(arguments.keys())}"
                
                return self.add_multiple_notes(
                    arguments["track_identifier"],
                    arguments["note_data"]
                )
            else:
                return f"Unknown tool: {tool_name}"
                
        except KeyError as e:
            logger.error(f"KeyError in execute_tool: {e}")
            logger.error(f"Tool: {tool_name}, Arguments: {arguments}")
            return f"Error: Missing required parameter {e} for tool {tool_name}"
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing tool {tool_name}: {str(e)}"
    
    def process_query_with_chaining(self, user_query: str, max_rounds: int = 10) -> str:
        """Process user query with multi-round tool calling support"""
        if not self.client:
            return "Error: Claude API not configured"
        
        try:
            # Always get current track context first
            track_context = self.list_tracks()
            
            # Provide context to Claude upfront
            context_message = f"Current REAPER project state:\n{track_context}\n\nUser request: {user_query}"
            
            messages = [
                {
                    "role": "user",
                    "content": context_message
                }
            ]
            
            results = []
            round_count = 0
            
            while round_count < max_rounds:
                round_count += 1
                logger.info(f"Tool calling round {round_count}")
                
                # Get response from Claude
                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    tools=self.tools,
                    messages=messages
                )
                
                # Add Claude's response to messages
                messages.append({"role": "assistant", "content": response.content})
                
                # Check if Claude wants to use tools
                tool_calls = [content for content in response.content if content.type == "tool_use"]
                text_content = [content for content in response.content if content.type == "text"]
                
                logger.info(f"Round {round_count}: Found {len(tool_calls)} tool calls, {len(text_content)} text responses")
                
                if not tool_calls:
                    # No more tools to call, add final text response
                    logger.info(f"No more tool calls - stopping at round {round_count}")
                    for content in text_content:
                        results.append(content.text)
                    break
                else:
                    # Log what tools Claude wants to call
                    tool_names = [tc.name for tc in tool_calls]
                    logger.info(f"Claude wants to call tools: {tool_names}")
                    
                    # Also log any text content in this round
                    if text_content:
                        for content in text_content:
                            logger.info(f"Claude text in round {round_count}: {content.text[:100]}...")
                            results.append(f"Round {round_count} text: {content.text}")
                
                # Execute tools and prepare results
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.name
                    tool_args = tool_call.input
                    tool_id = tool_call.id
                    
                    # Execute the tool
                    result = self.execute_tool(tool_name, tool_args)
                    results.append(f"Round {round_count} - {tool_name}: {result}")
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result
                    })
                
                # Add tool results to conversation
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
            
            if round_count >= max_rounds:
                results.append(f"Reached maximum rounds ({max_rounds}). Stopping here.")
            
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error in chained processing: {e}")
            return f"Error in chained processing: {str(e)}"

def main():
    """Main function for testing"""
    controller = ReaperController()
    
    print("REAPER Controller with Claude API")
    print("Available commands:")
    print("- Add track: 'Create a track called Bass'")
    print("- Delete track: 'Delete the track named Bass'")
    print("- Add FX: 'Add ReaSynth to the Bass track'")
    print("- Remove FX: 'Remove FX at index 0 from Bass track'")
    print("- List tracks: 'Show me all tracks'")
    print("- List FX: 'Show me all FX on the Bass track'")
    print("- Inspect FX: 'Show me all parameters of FX 0 on track Bass'")
    print("- Set parameter: 'Set parameter 2 of FX 0 on Bass track to 0.75'")
    print("- Multiply parameter: 'Multiply parameter 6 of FX 0 on Bass track by 1.5'")
    print("- Complex chaining: 'Create 3 tracks named Drums, Bass, Guitar and add ReaSynth to each'")
    print("- MIDI operations: 'Add multiple notes to track 1', 'Transpose track 1 up an octave'")
    print("\nAll queries use intelligent chaining - Claude will stop naturally when complete!")
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("Enter command: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input:
                # Always use chaining - Claude will naturally stop when no more tools are needed
                result = controller.process_query_with_chaining(user_input)
                print(f"Result: {result}\n")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()
