// VoiceButton.jsx
import React, { useState, useRef } from 'react'

const VoiceButton = ({ onVoiceInput, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

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
      
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = event => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(t => t.stop())

        // Process the audio
        setIsProcessing(true)
        const text = await convertAudioToText(blob)
        setIsProcessing(false)
        
        if (text && text.trim()) {
          onVoiceInput(text)
        }
      }

      mediaRecorderRef.current.start()
      setIsRecording(true)
    } catch (error) {
      console.error('Error accessing microphone:', error)
      alert('Unable to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const convertAudioToText = async (audioBlob) => {
    try {
      // For now, return placeholder text since we don't want this button to call transcribe
      // In the future, this could use local speech recognition or a different service
      console.log('Voice button audio recorded, but not sending to transcribe endpoint')
      return "Voice input detected - transcription service not connected to this button"
    } catch (error) {
      console.error('Error in voice processing:', error)
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

  return (
    <button
      onClick={handleClick}
      disabled={disabled || isProcessing}
      title={isRecording ? 'Stop voice recording' : 'Start voice-to-text'}
      className={`
        voice-play-button ${isRecording ? 'playing' : ''} ${isProcessing ? 'processing' : ''}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {isProcessing ? '⏳' : isRecording ? '⏹️' : '🎤'}
    </button>
  )
}

export default VoiceButton
