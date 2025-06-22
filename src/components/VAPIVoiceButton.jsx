import React, { useState, useRef, useEffect } from 'react'

const VAPIVoiceButton = ({ onVoiceResponse, onError, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [callId, setCallId] = useState(null)
  const [recordingTime, setRecordingTime] = useState(0)
  
  const websocketRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const audioContextRef = useRef(null)
  const timerRef = useRef(null)
  const streamRef = useRef(null)

  useEffect(() => {
    // Initialize WebSocket connection
    connectWebSocket()
    
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  const connectWebSocket = () => {
    try {
      websocketRef.current = new WebSocket('ws://localhost:8765')
      
      websocketRef.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
      }
      
      websocketRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data)
        handleWebSocketMessage(data)
      }
      
      websocketRef.current.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        setCallId(null)
        // Try to reconnect after 3 seconds
        setTimeout(() => {
          if (!isRecording) {
            connectWebSocket()
          }
        }, 3000)
      }
      
      websocketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setIsConnected(false)
    }
  }

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'call_started':
        console.log('VAPI call started:', data.call_id)
        setCallId(data.call_id)
        break
        
      case 'call_ended':
        console.log('VAPI call ended')
        setCallId(null)
        break
        
      case 'vapi_response':
        console.log('VAPI response:', data.data)
        if (data.data && data.data.transcript) {
          onVoiceResponse(data.data.transcript)
        }
        break
        
      case 'call_error':
        console.error('VAPI call error:', data.error)
        setCallId(null)
        if (onError) onError()
        if (data.error && data.error.includes('not configured')) {
          alert('VAPI is not configured. Please check your .env file in the backend directory.')
        } else {
          alert('Voice service error: ' + data.error)
        }
        break
        
      default:
        console.log('Unknown WebSocket message:', data)
    }
  }

  const startRecording = async () => {
    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
          channelCount: 1,
        }
      })
      
      streamRef.current = stream
      
      // Create audio context for processing
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      
      // Create media recorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      // Start VAPI call
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.send(JSON.stringify({
          type: 'start_call'
        }))
      }
      
      // Handle audio data
      mediaRecorderRef.current.ondataavailable = async (event) => {
        if (event.data.size > 0 && callId) {
          // Convert to raw audio data
          const arrayBuffer = await event.data.arrayBuffer()
          const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
          
          // Convert to 16-bit PCM
          const pcmData = convertToPCM(audioBuffer)
          
          // Send to WebSocket
          if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
            websocketRef.current.send(JSON.stringify({
              type: 'audio_chunk',
              audio: btoa(String.fromCharCode(...new Uint8Array(pcmData)))
            }))
          }
        }
      }
      
      // Start recording
      mediaRecorderRef.current.start(100) // Send chunks every 100ms
      setIsRecording(true)
      setRecordingTime(0)
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1)
      }, 1000)
      
    } catch (error) {
      if (onError) onError()
      console.error('Error starting recording:', error)
      alert('Unable to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      clearInterval(timerRef.current)
      
      // End VAPI call
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.send(JSON.stringify({
          type: 'end_call'
        }))
      }
      
      // Stop microphone
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
      
      setRecordingTime(0)
    }
  }

  const convertToPCM = (audioBuffer) => {
    const channelData = audioBuffer.getChannelData(0) // Mono
    const pcmData = new Int16Array(channelData.length)
    
    for (let i = 0; i < channelData.length; i++) {
      // Convert float32 to int16
      const sample = Math.max(-1, Math.min(1, channelData[i]))
      pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
    }
    
    return pcmData.buffer
  }

  const handleClick = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const getIcon = () => {
    if (!isConnected) return '🔴'
    if (isRecording) return '⏹️'
    return '🎤'
  }

  const getTooltip = () => {
    if (!isConnected) return 'Connecting to voice service...'
    if (isRecording) return 'Recording... click to stop'
    return 'Click to start voice conversation with VAPI'
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled || !isConnected}
      title={getTooltip()}
      className={`
        relative flex items-center justify-center w-8 h-8 rounded-full
        transition-transform hover:scale-110 focus:outline-none
        ${isRecording
          ? 'bg-gradient-to-r from-red-500 to-pink-500'
          : isConnected
          ? 'bg-gradient-to-r from-green-500 to-emerald-500'
          : 'bg-gradient-to-r from-gray-500 to-gray-600'}
        ${disabled || !isConnected ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <span className="text-white">{getIcon()}</span>
      {isRecording && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
      )}
    </button>
  )
}

export default VAPIVoiceButton 