import React, { useState, useRef, useEffect } from 'react'

const AudioMessage = ({ file, sender }) => {
  const [isLoaded, setIsLoaded] = useState(false)
  const [error, setError] = useState(null)
  const audioRef = useRef(null)

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleCanPlay = () => {
      setIsLoaded(true)
      setError(null)
    }

    const handleError = (e) => {
      console.error('Audio error:', e)
      setError('Error playing audio file')
    }

    // Add event listeners
    audio.addEventListener('canplay', handleCanPlay)
    audio.addEventListener('error', handleError)

    return () => {
      audio.removeEventListener('canplay', handleCanPlay)
      audio.removeEventListener('error', handleError)
    }
  }, [file])

  // Debug: log the file object
  console.log('AudioMessage file object:', file)
  console.log('File name:', file?.name)
  console.log('File type:', file?.type)

  const getDisplayName = () => {
    if (!file || !file.name) {
      return 'Unknown Audio'
    }
    return file.name.replace(/\.wav$/i, '')
  }

  return (
    <div className="audio-message-container">
      <div className="audio-player">
        <div className="audio-info">
          <div className="audio-filename">
            {getDisplayName()}
            {error && <span className="text-red-400 ml-2">⚠️ {error}</span>}
            {!isLoaded && !error && <span className="text-yellow-400 ml-2">⏳ Loading...</span>}
          </div>
          <div className="audio-controls">
            <audio
              ref={audioRef}
              src={URL.createObjectURL(file)}
              preload="metadata"
              controls
              className="custom-audio-controls"
            />
          </div>
        </div>
        
        <div className="audio-icon">
          {sender === 'user' ? '🎵' : '🎼'}
        </div>
      </div>
    </div>
  )
}

export default AudioMessage
