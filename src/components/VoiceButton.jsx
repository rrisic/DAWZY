// VoiceButton.jsx
import React, { useState, useRef } from 'react'

const VoiceButton = ({ onVoiceInput, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false)
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

        // Use OpenAI Whisper for transcription
        const text = await convertAudioToText(blob)
        onVoiceInput(text)
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

      if (result.success && result.transcript) {
        console.log('Transcribed text:', result.transcript)
        return result.transcript
      } else {
        console.error('Transcription failed:', result.error)
        return "Failed to transcribe audio. Please try again."
      }
    } catch (error) {
      console.error('Error sending audio to backend:', error)
      return "Failed to send audio for transcription. Please try again."
    }
  }

  const handleClick = () => {
    isRecording ? stopRecording() : startRecording()
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      title={isRecording ? 'Stop voice recording' : 'Start voice-to-text'}
      className={`
        voice-play-button ${isRecording ? 'playing' : ''}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {isRecording ? '⏹️' : '🎤'}
    </button>
  )
}

export default VoiceButton
