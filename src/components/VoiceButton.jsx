// VoiceButton.jsx
import React, { useState, useRef, useEffect } from 'react'

const VoiceButton = ({ onVoiceInput, disabled = false, isVoiceMode = false, onModeChange, onTranscriptionUpdate, onRecordingStateChange }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentTranscription, setCurrentTranscription] = useState('')
  const [audioLevel, setAudioLevel] = useState(0)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const microphoneRef = useRef(null)
  const streamRef = useRef(null)
  const transcriptionIntervalRef = useRef(null)

  // Real-time transcription settings
  const TRANSCRIPTION_INTERVAL = 3000 // Send audio for transcription every 3 seconds
  const AUDIO_THRESHOLD = 0.01 // Minimum audio level to consider "speaking"

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
          channelCount: 1,
        }
      })
      
      streamRef.current = stream
      
      // Set up audio analysis for level monitoring
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      analyserRef.current = audioContextRef.current.createAnalyser()
      microphoneRef.current = audioContextRef.current.createMediaStreamSource(stream)
      
      microphoneRef.current.connect(analyserRef.current)
      analyserRef.current.fftSize = 256
      
      const bufferLength = analyserRef.current.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      
      // Start audio level monitoring
      const checkAudioLevel = () => {
        if (!isRecording) return
        
        analyserRef.current.getByteFrequencyData(dataArray)
        const average = dataArray.reduce((a, b) => a + b) / bufferLength
        const normalizedLevel = average / 255
        
        setAudioLevel(normalizedLevel)
        requestAnimationFrame(checkAudioLevel)
      }
      
      checkAudioLevel()

      // Set up MediaRecorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = event => {
        audioChunksRef.current.push(event.data)
      }

      // Handle recording stop
      mediaRecorderRef.current.onstop = async () => {
        console.log('Recording stopped, processing audio...')
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        console.log('Final audio blob size:', blob.size, 'bytes')
        stream.getTracks().forEach(t => t.stop())
        
        // Clean up audio analysis
        if (audioContextRef.current) {
          audioContextRef.current.close()
        }
        
        // Clear transcription interval
        if (transcriptionIntervalRef.current) {
          clearInterval(transcriptionIntervalRef.current)
          transcriptionIntervalRef.current = null
        }

        // Process the audio
        setIsProcessing(true)
        const text = await convertAudioToText(blob)
        setIsProcessing(false)
        
        if (text && text.trim()) {
          console.log('Final transcription result:', text)
          if (isVoiceMode) {
            // In voice mode, update transcription
            setCurrentTranscription(prev => {
              const newTranscription = prev + ' ' + text
              onTranscriptionUpdate?.(newTranscription.trim())
              return newTranscription
            })
          } else {
            // In normal mode, send directly
            console.log('Sending to chat:', text)
            onVoiceInput(text)
          }
        } else {
          console.log('No transcription result, not sending')
        }
      }

      // Start recording
      if (isVoiceMode) {
        // Real-time transcription mode
        mediaRecorderRef.current.start(1000) // Collect data every second
        setIsRecording(true)
        onRecordingStateChange?.(true)
        setCurrentTranscription('')

        // Start periodic transcription
        transcriptionIntervalRef.current = setInterval(async () => {
          if (isRecording && audioChunksRef.current.length > 0) {
            await processCurrentAudio()
          }
        }, TRANSCRIPTION_INTERVAL)
      } else {
        // Normal voice mode - single recording
        mediaRecorderRef.current.start()
        setIsRecording(true)
      }

    } catch (error) {
      console.error('Error accessing microphone:', error)
      alert('Unable to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      onRecordingStateChange?.(false)
      setAudioLevel(0)
      
      // Clear transcription interval
      if (transcriptionIntervalRef.current) {
        clearInterval(transcriptionIntervalRef.current)
        transcriptionIntervalRef.current = null
      }
      
      // Clean up
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }

  const processCurrentAudio = async () => {
    if (audioChunksRef.current.length === 0) return

    try {
      console.log('Processing audio chunks:', audioChunksRef.current.length)
      
      // Create a copy of current audio chunks
      const audioChunks = [...audioChunksRef.current]
      audioChunksRef.current = [] // Clear for next interval
      
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      console.log('Audio blob size:', blob.size, 'bytes')
      
      if (blob.size < 1000) {
        console.log('Audio blob too small, skipping')
        return
      }
      
      const text = await convertAudioToText(blob)
      
      if (text && text.trim()) {
        console.log('Received transcription:', text)
        setCurrentTranscription(prev => {
          const newTranscription = prev + ' ' + text
          onTranscriptionUpdate?.(newTranscription.trim())
          return newTranscription
        })
      } else {
        console.log('No transcription received or empty text')
      }
    } catch (error) {
      console.error('Error processing audio:', error)
    }
  }

  const convertAudioToText = async (audioBlob) => {
    try {
      console.log('Converting audio to text, blob size:', audioBlob.size)
      
      // Convert blob to base64
      const reader = new FileReader()
      const base64Promise = new Promise((resolve) => {
        reader.onload = () => {
          const base64Audio = reader.result.split(',')[1] // Remove data URL prefix
          resolve(base64Audio)
        }
      })
      reader.readAsDataURL(audioBlob)
      const base64Audio = await base64Promise

      console.log('Sending to backend for transcription...')

      // Send to backend for transcription
      const response = await fetch('http://localhost:5000/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          audio: base64Audio
        })
      })

      const result = await response.json()
      console.log('Backend response:', result)

      if (result.success && result.transcript) {
        console.log('Transcription successful:', result.transcript)
        return result.transcript
      } else {
        console.error('Transcription failed:', result.error)
        return null
      }
    } catch (error) {
      console.error('Error sending audio to backend:', error)
      return null
    }
  }

  const handleClick = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const toggleMode = () => {
    if (isRecording) {
      stopRecording()
    }
    setCurrentTranscription('')
    onTranscriptionUpdate?.('')
    onModeChange(!isVoiceMode)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (transcriptionIntervalRef.current) {
        clearInterval(transcriptionIntervalRef.current)
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [])

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleClick}
        disabled={disabled || isProcessing}
        title={isRecording ? 'Stop voice recording' : (isVoiceMode ? 'Start real-time transcription' : 'Start voice-to-text')}
        className={`
          voice-play-button ${isRecording ? 'playing' : ''} ${isProcessing ? 'processing' : ''}
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        {isProcessing ? '⏳' : isRecording ? '⏹️' : '🎤'}
      </button>
      
      {/* Mode Toggle */}
      <button
        onClick={toggleMode}
        disabled={disabled || isRecording}
        title={isVoiceMode ? 'Switch to text mode' : 'Switch to voice mode'}
        className={`
          voice-play-button ${isVoiceMode ? 'voice-mode-active' : ''}
          ${disabled || isRecording ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        {isVoiceMode ? '📝' : '🎤'}
      </button>
      
      {/* Audio Level Indicator */}
      {isRecording && (
        <div className="flex items-center gap-1">
          <div className="w-2 h-8 bg-gray-600 rounded-full overflow-hidden">
            <div 
              className="bg-green-400 transition-all duration-100 rounded-full"
              style={{ 
                height: `${Math.min(audioLevel * 100, 100)}%`,
                background: audioLevel > AUDIO_THRESHOLD ? '#10b981' : '#6b7280'
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default VoiceButton
