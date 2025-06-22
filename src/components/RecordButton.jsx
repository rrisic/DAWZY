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

        // Call convert-to-midi endpoint for MIDI conversion
        try {
          console.log('Sending audio to convert-to-midi endpoint for MIDI conversion...')
          
          // Convert blob to base64
          const reader = new FileReader()
          const base64Promise = new Promise((resolve) => {
            reader.onload = () => {
              const base64Audio = reader.result.split(',')[1] // Remove data URL prefix
              resolve(base64Audio)
            }
          })
          reader.readAsDataURL(wavBlob)
          const base64Audio = await base64Promise

          // Send to backend for MIDI conversion only
          const response = await fetch('http://localhost:5000/convert-to-midi', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              audio: base64Audio
            })
          })

          const result = await response.json()
          
          if (result.success) {
            console.log('Convert-to-MIDI endpoint response:', result)
            if (result.midi_conversion) {
              if (result.midi_conversion.success) {
                console.log('MIDI conversion successful:', result.midi_conversion.message)
                alert(`Recording processed! ${result.midi_conversion.message}`)
              } else {
                console.error('MIDI conversion failed:', result.midi_conversion.error)
                alert(`MIDI conversion failed: ${result.midi_conversion.error}`)
              }
            }
          } else {
            console.error('Convert-to-MIDI endpoint failed:', result.error)
            alert(`Processing failed: ${result.error}`)
          }
        } catch (error) {
          console.error('Error calling convert-to-midi endpoint:', error)
          alert('Failed to process recording for MIDI conversion')
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
