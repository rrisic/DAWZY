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
            return f"Successfully created track: '{track_name}' (ID: {new_track.id})"
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
        else:
            return f"Unknown tool: {tool_name}"
    
    def process_query(self, user_query: str) -> str:
        """Process user query using Claude API with tool calls"""
        if not self.client:
            return "Error: Claude API not configured"
        
        try:
            # Initial message to Claude
            messages = [
                {
                    "role": "user",
                    "content": user_query
                }
            ]
            
            # Get response from Claude
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                tools=self.tools,
                messages=messages
            )
            
            # Process tool calls
            results = []
            tool_results = []
            
            for content in response.content:
                if content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input
                    tool_id = content.id
                    
                    # Execute the tool
                    result = self.execute_tool(tool_name, tool_args)
                    results.append(f"Executed {tool_name}: {result}")
                    
                    # Prepare tool result for Claude
                    tool_results.append({
                        "tool_use_id": tool_id,
                        "content": result
                    })
                elif content.type == "text":
                    results.append(content.text)
            
            # If there were tool calls, get Claude's final response
            if tool_results:
                messages.extend([
                    {"role": "assistant", "content": response.content},
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_result["tool_use_id"],
                                "content": tool_result["content"]
                            } for tool_result in tool_results
                        ]
                    }
                ])
                
                final_response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    tools=self.tools,
                    messages=messages
                )
                
                for content in final_response.content:
                    if content.type == "text":
                        results.append(content.text)
            
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Error processing query: {str(e)}"

    def process_query_with_chaining(self, user_query: str, max_rounds: int = 5) -> str:
        """Process user query with multi-round tool calling support"""
        if not self.client:
            return "Error: Claude API not configured"
        
        try:
            messages = [
                {
                    "role": "user",
                    "content": user_query
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
                
                if not tool_calls:
                    # No more tools to call, add final text response
                    for content in response.content:
                        if content.type == "text":
                            results.append(content.text)
                    break
                
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
    print("- Complex chaining: 'Create 3 tracks named Drums, Bass, Guitar and add ReaSynth to each'")
    print("\nModes:")
    print("- Type 'chain:' before your command for multi-round tool calling")
    print("- Type 'simple:' or just enter command for single-round tool calling")
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("Enter command: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input:
                if user_input.startswith('chain:'):
                    query = user_input[6:].strip()
                    result = controller.process_query_with_chaining(query)
                    print(f"Chained Result: {result}\n")
                elif user_input.startswith('simple:'):
                    query = user_input[7:].strip()
                    result = controller.process_query(query)
                    print(f"Simple Result: {result}\n")
                else:
                    result = controller.process_query(user_input)
                    print(f"Result: {result}\n")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()
