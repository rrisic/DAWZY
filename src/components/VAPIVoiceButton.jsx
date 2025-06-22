import React, { useState, useRef, useEffect } from 'react'

const VAPIVoiceButton = ({ onVoiceModeChange, onVoiceResponse, disabled = false }) => {
  const [isVoiceMode, setIsVoiceMode] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  
  const mediaRecorderRef = useRef(null)
  const timerRef = useRef(null)
  const streamRef = useRef(null)
  const audioChunksRef = useRef([])

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
      audioChunksRef.current = []
      
      // Create media recorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      // Handle audio data
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorderRef.current.onstop = async () => {
        // Create audio blob
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        
        // For now, just log that audio was recorded since this button shouldn't call transcribe
        console.log('VAPI Voice button audio recorded, but not sending to transcribe endpoint')
        
        // In the future, this could integrate with VAPI or another voice service
        // For now, just provide a placeholder response
        onVoiceResponse("Voice input detected - VAPI integration not connected to transcribe endpoint")
      }
      
      // Start recording
      mediaRecorderRef.current.start(100) // Collect chunks every 100ms
      setIsRecording(true)
      setRecordingTime(0)
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1)
      }, 1000)
      
    } catch (error) {
      console.error('Error starting recording:', error)
      alert('Unable to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      clearInterval(timerRef.current)
      
      // Stop microphone
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
      
      setRecordingTime(0)
    }
  }

  const toggleVoiceMode = () => {
    const newMode = !isVoiceMode
    setIsVoiceMode(newMode)
    onVoiceModeChange(newMode)
    
    if (newMode) {
      // Entering voice mode - start recording
      startRecording()
    } else {
      // Exiting voice mode - stop recording
      stopRecording()
    }
  }

  const getIcon = () => {
    if (isVoiceMode) return '⏹️'
    return '🎤'
  }

  const getTooltip = () => {
    if (isVoiceMode) return 'Voice mode active - click to stop'
    return 'Click to start voice conversation'
  }

  return (
    <button
      onClick={toggleVoiceMode}
      disabled={disabled}
      title={getTooltip()}
      className={`
        relative flex items-center justify-center w-8 h-8 rounded-full
        transition-transform hover:scale-110 focus:outline-none
        ${isVoiceMode
          ? 'bg-gradient-to-r from-red-500 to-pink-500'
          : 'bg-gradient-to-r from-green-500 to-emerald-500'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <span className="text-white">{getIcon()}</span>
      {isVoiceMode && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
      )}
    </button>
  )
}

export default VAPIVoiceButton