// RecordButton.jsx
import React, { useState, useRef } from 'react'

const RecordButton = ({ onAudioRecorded, disabled = false, maxDuration = 5 }) => {
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerRef = useRef(null)
  const autoStopRef = useRef(null)

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
          channelCount: 1,
        }
      })

      // choose a supported MIME type
      let mimeType = 'audio/webm;codecs=opus'
      if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/webm'
      if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/mp4'
      if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = 'audio/wav'

      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000
      })
      audioChunksRef.current = []

      mediaRecorderRef.current.ondataavailable = event => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorderRef.current.onstop = async () => {
        // assemble blob
        const blob = new Blob(audioChunksRef.current, { type: mimeType })

        // convert to WAV for compatibility
        const wavBlob = await convertToWav(blob)
        const file = new File([wavBlob], 'temp.wav', { type: 'audio/wav' })

        // Save to local machine for debugging
        try {
          const saveResult = await window.musicAssistant.saveAudioRecording(wavBlob, 'temp.wav')
          console.log('Save result:', saveResult)
          if (saveResult.success) {
            console.log('Recording saved to:', saveResult.filePath)
            console.log('Filename from save result:', saveResult.filename)
            // Update the file with the correct sequential filename
            const updatedFile = new File([wavBlob], saveResult.filename, { type: 'audio/wav' })
            console.log('Updated file object:', updatedFile)
            console.log('Updated file name:', updatedFile.name)
            onAudioRecorded(updatedFile)
          } else {
            console.error('Failed to save recording:', saveResult.error)
            // Still send the file to chat even if save failed
            onAudioRecorded(file)
          }
        } catch (error) {
          console.error('Error saving recording:', error)
          // Still send the file to chat even if save failed
          onAudioRecorded(file)
        }

        // stop mic
        stream.getTracks().forEach(t => t.stop())

        // reset timer
        clearInterval(timerRef.current)
        clearTimeout(autoStopRef.current)

        // reset recording state
        setRecordingTime(0)
      }

      // start recording
      mediaRecorderRef.current.start(100)
      setIsRecording(true)
      setRecordingTime(0)

      // timer for UI
      timerRef.current = setInterval(() => {
        setRecordingTime(t => t + 1)
      }, 1000)

      // auto-stop after maxDuration seconds
      autoStopRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && isRecording) {
          mediaRecorderRef.current.stop()
          setIsRecording(false)
        }
      }, maxDuration * 1000)

    } catch (error) {
      console.error('Error accessing microphone:', error)
      alert('Unable to access microphone. Please check permissions.')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      clearInterval(timerRef.current)
      clearTimeout(autoStopRef.current)
    }
  }

  // simple WAV conversion fallback
  const convertToWav = async (blob) => {
    return blob  // assume it's already a compatible format; or implement AudioBuffer→WAV here
  }

  const handleClick = () => {
    if (isRecording) stopRecording()
    else startRecording()
  }

  const getIcon = () => isRecording ? '⏹️' : '🎵'
  const getTooltip = () => (
    isRecording
      ? 'Recording... click to stop early'
      : `Click to record up to ${maxDuration}s of melody`
  )

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      title={getTooltip()}
      className={`
        voice-play-button record-button ${isRecording ? 'playing' : ''}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
      `}
    >
      {isRecording ? '⏹️' : '🔴'}
    </button>
  )
}

export default RecordButton
