# Beatoven.ai Music Generation Setup

This guide will help you set up the Beatoven.ai music generation feature to replace Lyria RealTime.

## Prerequisites

1. **Beatoven.ai API Key**: You'll need a Beatoven.ai API key to access their music generation service
2. **Python Environment**: Make sure your backend virtual environment is activated
3. **REAPER**: For importing generated music tracks

## Setup Steps

### 1. Get Beatoven.ai API Key

1. Go to [Beatoven.ai](https://beatoven.ai)
2. Sign up for an account
3. Navigate to your API settings
4. Generate a new API key
5. Copy the generated API key

### 2. Configure Environment Variables

Create or update the `.env` file in the `backend/` directory:

```bash
# Existing OpenAI key
OPENAI_API_KEY=your_openai_api_key_here

# Beatoven.ai key (replace the old Google AI key)
BEATOVEN_AI_API_KEY=your_beatoven_ai_api_key_here
```

### 3. Install Dependencies

Make sure your virtual environment is activated, then install the updated dependencies:

```bash
cd backend
pip install -r requirements.txt
```

### 4. Test the Setup

1. Start the backend:
   ```bash
   cd backend
   python app.py
   ```

2. Start the frontend:
   ```bash
   npm run dev
   ```

3. Test music generation by asking DAWZY to create music:
   - "Create a techno track with heavy bass"
   - "Generate a peaceful ambient melody"
   - "Make a drum and bass beat at 140 BPM"
   - "can you generate me a snare drumline please"

## How It Works

1. **User Input**: You ask DAWZY to create music through voice or text
2. **OpenAI Processing**: OpenAI GPT analyzes your request and creates structured instructions
3. **Beatoven.ai Generation**: Beatoven.ai generates the actual music track based on your request
4. **Async Processing**: The system polls for completion and downloads the generated track
5. **REAPER Integration**: The generated track is automatically imported into REAPER
6. **File Management**: Tracks are saved with descriptive filenames based on your request

## Current Implementation

The system now:
- ✅ Processes music generation requests through OpenAI GPT
- ✅ Creates structured instructions for Beatoven.ai
- ✅ Generates high-quality music using Beatoven.ai's async API
- ✅ Polls for completion with proper timeout handling
- ✅ Downloads and saves generated tracks
- ✅ Imports tracks into REAPER automatically
- ✅ Displays detailed track information in the chat
- ✅ Saves files with descriptive names based on user requests

## Beatoven.ai Features

Beatoven.ai provides:
- **High-quality music generation** with professional production quality
- **Dynamic, fluid audio** with rich harmonic content
- **Multiple genres and styles** support
- **Async processing** for complex compositions
- **Stem separation** (bass, chords, melody, percussion)
- **Studio-quality output** that sounds like professional production

## API Workflow

1. **Compose Request**: Send prompt to `/api/v1/tracks/compose`
2. **Get Task ID**: Receive task_id for tracking
3. **Poll Status**: Check `/api/v1/tasks/{task_id}` every 5 seconds
4. **Download Track**: When status is "composed", download the track
5. **Import to REAPER**: Add the track to your DAW

## Troubleshooting

### API Key Issues
- Make sure your Beatoven.ai API key is valid and has the necessary permissions
- Check that the key is correctly set in the `.env` file

### Import Errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that your virtual environment is activated

### REAPER Integration
- Make sure REAPER is running
- Verify that the `python-reapy` package is installed correctly
- Check REAPER's console for any error messages

### Beatoven.ai API Issues
- Check your Beatoven.ai account for usage limits and quotas
- Verify the API endpoint is accessible from your network
- Check the Beatoven.ai status page for any service issues
- Note: Music generation can take 1-5 minutes depending on complexity

## Example Usage

```
User: "can you generate me a snare drumline please and make it 120 bpm to line up with my other track"
DAWZY: "I'll generate a snare drumline at 120 BPM for you!"

[Music Generation Result]
Track Details:
- Description: snare drumline at 120 bpm
- Task ID: ccb84650-7b4a-4d00-9f80-8a6427ca21aa_1
- Format: WAV

✅ Track imported into REAPER
```

The generated track will appear in REAPER as a new audio item on a new track, ready for further editing and production.

## File Naming

Generated files are named based on your request:
- `"can you generate me a snare drumline please"` → `snare_drumline_please_1234567890.wav`
- `"create a dark techno track"` → `create_a_dark_techno_track_1234567890.wav`
- `"peaceful ambient melody"` → `peaceful_ambient_melody_1234567890.wav`

## Cost Considerations

Beatoven.ai may have usage-based pricing. Check their pricing page for current rates and ensure your account has sufficient credits for music generation.

## API Endpoints

- **Base URL**: `https://public-api.beatoven.ai`
- **Compose**: `POST /api/v1/tracks/compose`
- **Status**: `GET /api/v1/tasks/{task_id}`
- **Authentication**: Bearer token in Authorization header 

**Description**

`status`: The value can be one of the following -

- `composing`: The task has been put in the queue and is being processed
- `running`: The task has started running
- `composed`:  The composition task has finished and the generated assets are available 