# DAWZY - Music Production Assistant

A modern music production assistant with voice interaction and audio recording capabilities.

## Features

### 🎤 Voice Button
- **Purpose**: Voice-to-text functionality for hands-free interaction with the AI assistant
- **Current State**: Records audio and provides placeholder text (VAPI integration pending)
- **Visual Feedback**: 
  - Purple gradient when idle
  - Red gradient with pulsing animation when recording
  - Microphone icon that changes based on state
  - Ping animation during recording

### 🎵 Record Button (MIDI Conversion)
- **Purpose**: Record humming, melodies, or other sounds for conversion to MIDI tracks
- **Current State**: Records audio and sends to chat (MIDI conversion service pending)
- **Visual Feedback**:
  - Blue gradient when idle
  - Red gradient with timer when recording
  - Green gradient when ready to send
  - Music note icon that changes to stop/send icons
  - Recording timer display
  - State labels ("Record MIDI", "Ready to send")

### 🎧 Audio Messages
- **Purpose**: Display recorded audio files in the chat with playback controls
- **Features**:
  - Play/pause controls
  - Progress bar with time display
  - File name display
  - Styled to match the chat interface

## Technical Implementation

### Components
- `VoiceButton.jsx` - Handles voice recording and text conversion
- `RecordButton.jsx` - Handles audio recording for MIDI conversion
- `AudioMessage.jsx` - Displays audio files with playback controls
- `ChatWindow.jsx` - Main chat interface with integrated buttons

### Audio Recording
- Uses Web Audio API and MediaRecorder
- Supports multiple audio formats (WebM, WAV)
- Automatic microphone permission handling
- Error handling for unsupported browsers/devices

### Future Integrations
- **VAPI**: Voice-to-text conversion for the voice button
- **MIDI Conversion**: Audio-to-MIDI conversion service for the record button
- **Reaper Integration**: Automatic MIDI import into Reaper DAW

## Development

### Running the App
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run Electron app
npm run electron-dev
```

### Project Structure
```
src/
├── components/
│   ├── ChatWindow.jsx      # Main chat interface
│   ├── VoiceButton.jsx     # Voice recording component
│   ├── RecordButton.jsx    # Audio recording component
│   └── AudioMessage.jsx    # Audio playback component
├── App.jsx                 # Root component
└── index.css              # Styling and animations
```

## UI/UX Design

### Design System
- **Colors**: Purple, blue, and pink gradients
- **Animations**: Smooth transitions, pulse, and ping effects
- **Typography**: Inter font family
- **Layout**: Glassmorphism effects with backdrop blur

### Accessibility
- Tooltips for all interactive elements
- Keyboard navigation support
- Screen reader friendly labels
- High contrast color schemes

## Browser Compatibility

### Required APIs
- MediaRecorder API
- getUserMedia API
- Web Audio API
- File API

### Supported Browsers
- Chrome 66+
- Firefox 60+
- Safari 14+
- Edge 79+

## Next Steps

1. **VAPI Integration**: Replace placeholder text conversion with actual VAPI service
2. **MIDI Conversion**: Implement audio-to-MIDI conversion backend service
3. **Reaper Integration**: Add automatic MIDI import functionality
4. **Audio Processing**: Add audio effects and processing capabilities
5. **Multi-track Support**: Support for multiple simultaneous recordings 