import React, { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'

const AIVoiceResponse = React.memo(({ text, audioBase64, messageId, onPlayStart, onPlayEnd }) => {
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

  const handleCanPlay = useCallback(() => {
    setIsLoaded(true)
    setError(null)
  }, [])

  const handlePlay = useCallback(() => {
    setIsPlaying(true)
    onPlayStart?.()
  }, [onPlayStart])

  const handlePause = useCallback(() => {
    setIsPlaying(false)
  }, [])

  const handleEnded = useCallback(() => {
    setIsPlaying(false)
    onPlayEnd?.()
  }, [onPlayEnd])

  const handleError = useCallback((e) => {
    console.error('Audio error:', e)
    setError('Error playing audio')
    setIsPlaying(false)
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

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
  }, [handleCanPlay, handlePlay, handlePause, handleEnded, handleError])

  const handlePlayClick = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.play()
    }
  }, [])

  const handleStopClick = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
  }, [])

  return (
    <div className="ai-voice-response" data-message-id={messageId}>
      <div className="ai-text">
        <ReactMarkdown 
          className="markdown-content"
          components={{
            p: ({children}) => <div className="mb-2">{children}</div>,
            strong: ({children}) => <strong className="font-bold text-white">{children}</strong>,
            em: ({children}) => <em className="italic text-white">{children}</em>,
            ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
            li: ({children}) => <li className="text-white">{children}</li>,
            h1: ({children}) => <h1 className="text-xl font-bold text-white mb-2">{children}</h1>,
            h2: ({children}) => <h2 className="text-lg font-bold text-white mb-2">{children}</h2>,
            h3: ({children}) => <h3 className="text-md font-bold text-white mb-1">{children}</h3>
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
      
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
})

AIVoiceResponse.displayName = 'AIVoiceResponse'

export default AIVoiceResponse 