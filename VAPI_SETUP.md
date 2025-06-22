# VAPI Integration Setup

This guide explains how to set up VAPI for real-time voice conversation in DAWZY.

## Prerequisites

1. **VAPI Account**: Sign up at [vapi.ai](https://vapi.ai)
2. **API Key**: Get your VAPI API key from the dashboard
3. **Assistant ID** (optional): Create an assistant in VAPI dashboard

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

```env
# OpenAI API Key for LLM processing
OPENAI_API_KEY=your-openai-api-key-here

# VAPI API Key for real-time voice processing
VAPI_API_KEY=your-vapi-api-key-here

# VAPI Assistant ID (optional - can be created via VAPI dashboard)
VAPI_ASSISTANT_ID=your-vapi-assistant-id-here
```

## Python Dependencies

Install the required Python packages:

```bash
cd backend
pip install -r requirements.txt
```

## VAPI Configuration

### Option 1: Use VAPI Assistant ID
1. Go to [VAPI Dashboard](https://console.vapi.ai)
2. Create a new assistant
3. Configure the assistant with:
   - **Model**: GPT-4
   - **System Prompt**: "You are a helpful REAPER assistant..."
   - **Voice**: Choose your preferred voice
4. Copy the Assistant ID to your `.env` file

### Option 2: Let Backend Create Assistant
If you don't provide `VAPI_ASSISTANT_ID`, the backend will create a temporary assistant for each call.

## Usage

1. **Start DAWZY**: The backend will automatically start the WebSocket server on port 8765
2. **Voice Button**: Click the green microphone button (🎤) to start a voice conversation
3. **Real-time Processing**: Speak naturally - VAPI will transcribe your speech and respond with voice
4. **Integration**: Voice transcripts are automatically sent to the chat and processed by the LLM

## Architecture

### Frontend (Electron)
- **VAPIVoiceButton**: Real-time audio capture and WebSocket communication
- **WebSocket Client**: Streams audio chunks to backend
- **UI Feedback**: Visual indicators for connection and recording status

### Backend (Python)
- **WebSocket Server**: Handles real-time audio streaming
- **VAPI Client**: Manages VAPI calls and audio processing
- **Audio Processor**: Converts and buffers audio data
- **LLM Integration**: Processes voice transcripts through existing chat system

### Data Flow
1. User clicks voice button → Frontend starts recording
2. Audio chunks → WebSocket → Backend
3. Backend → VAPI → Speech-to-Text
4. Transcript → LLM → Response
5. Response → Chat interface

## Troubleshooting

### WebSocket Connection Issues
- Check if backend is running
- Verify port 8765 is not blocked
- Check browser console for connection errors

### VAPI Errors
- Verify API key is correct
- Check VAPI account has sufficient credits
- Ensure assistant is properly configured

### Audio Issues
- Check microphone permissions
- Verify audio format compatibility
- Check browser audio settings

## Security Notes

- API keys are stored in `.env` file (not committed to git)
- WebSocket server runs on localhost only
- Audio data is processed locally before sending to VAPI
- No audio data is stored permanently 