// VoiceButton.jsx
import React, { useState, useRef } from 'react'

const VoiceButton = ({ onVoiceInput, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = event => {
        audioChunksRef.current.push(event.data)
      }

      mediaRecorderRef.current.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' })
        stream.getTracks().forEach(t => t.stop())

        // Placeholder transcription (swap in VAPI/etc. here)
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
    // TODO: replace with real model/VAPI call
    return new Promise(resolve => {
      setTimeout(() => {
        resolve("🎤 (Transcribed text will appear here once VAPI is integrated.)")
      }, 1000)
    })
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
        relative flex items-center justify-center w-8 h-8 rounded-full
        transition-transform hover:scale-110 focus:outline-none
        ${isRecording
          ? 'bg-gradient-to-r from-red-500 to-pink-500'
          : 'bg-gradient-to-r from-purple-500 to-blue-500'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <span className="text-white">🎤</span>
    </button>
  )
}

export default VoiceButton
