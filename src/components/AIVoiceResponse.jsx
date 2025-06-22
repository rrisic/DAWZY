import React, { useState, useRef, useEffect } from 'react'

const AIVoiceResponse = ({ text, audioBase64, onPlayStart, onPlayEnd }) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const [error, setError] = useState(null)
  const audioRef = useRef(null)

  useEffect(() => {
    if (audioBase64) {
      // Convert base64 to blob
      const audioData = atob(audioBase64)
      const audioArray = new Uint8Array(audioData.length)
      for (let i = 0; i < audioData.length; i++) {
        audioArray[i] = audioData.charCodeAt(i)
      }
      const audioBlob = new Blob([audioArray], { type: 'audio/mpeg' })
      const audioUrl = URL.createObjectURL(audioBlob)
      
      if (audioRef.current) {
        audioRef.current.src = audioUrl
      }
    }
  }, [audioBase64])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleCanPlay = () => {
      setIsLoaded(true)
      setError(null)
    }

    const handlePlay = () => {
      setIsPlaying(true)
      onPlayStart?.()
    }

    const handlePause = () => {
      setIsPlaying(false)
    }

    const handleEnded = () => {
      setIsPlaying(false)
      onPlayEnd?.()
    }

    const handleError = (e) => {
      console.error('Audio error:', e)
      setError('Error playing audio')
      setIsPlaying(false)
    }

    // Add event listeners
    audio.addEventListener('canplay', handleCanPlay)
    audio.addEventListener('play', handlePlay)
    audio.addEventListener('pause', handlePause)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('error', handleError)

    return () => {
      audio.removeEventListener('canplay', handleCanPlay)
      audio.removeEventListener('play', handlePlay)
      audio.removeEventListener('pause', handlePause)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('error', handleError)
    }
  }, [onPlayStart, onPlayEnd])

  const handlePlayClick = () => {
    if (audioRef.current) {
      audioRef.current.play()
    }
  }

  const handleStopClick = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
  }

  return (
    <div className="ai-voice-response">
      <div className="ai-text">{text}</div>
      
      {audioBase64 && (
        <div className="ai-voice-controls">
          <button
            onClick={isPlaying ? handleStopClick : handlePlayClick}
            className={`voice-play-button ${isPlaying ? 'playing' : ''}`}
            title={isPlaying ? 'Stop AI voice' : 'Play AI voice'}
          >
            {isPlaying ? '⏹️' : '🔊'}
          </button>
          
          {!isLoaded && !error && (
            <span className="loading-indicator">⏳ Loading voice...</span>
          )}
          
          {error && (
            <span className="error-indicator">⚠️ {error}</span>
          )}
          
          {isPlaying && (
            <span className="playing-indicator">Speaking...</span>
          )}
        </div>
      )}
      
      <audio
        ref={audioRef}
        preload="metadata"
        style={{ display: 'none' }}
      />
    </div>
  )
}

export default AIVoiceResponse 