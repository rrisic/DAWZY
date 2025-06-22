import React, { useState, useEffect, useRef } from 'react'
import VoiceButton from './VoiceButton'
import RecordButton from './RecordButton'
import AudioMessage from './AudioMessage'
import AIVoiceResponse from './AIVoiceResponse'
import MusicGenerationResult from './MusicGenerationResult'

const ChatWindow = () => {
  const [messages, setMessages] = useState([
    { id: 1, sender: 'ai', text: 'Hi! I\'m DAWZY, your music production assistant. How can I help you today?' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(true)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const inputContainerRef = useRef(null)
  const lastAudioRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const scrollInputIntoView = () => {
    if (inputContainerRef.current) {
      inputContainerRef.current.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'end',
        inline: 'nearest'
      })
    }
  }

  const autoResizeTextarea = () => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
      
      // If the textarea is getting tall, scroll it into view
      if (textarea.scrollHeight > 100) {
        setTimeout(scrollInputIntoView, 100)
      }
    }
  }

  // Focus textarea when component mounts
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    autoResizeTextarea()
  }, [input])

  // Auto-play the latest AI audio response
  useEffect(() => {
    if (autoPlayEnabled) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage && lastMessage.sender === 'ai' && lastMessage.audio && lastAudioRef.current !== lastMessage.id) {
        lastAudioRef.current = lastMessage.id
        // Small delay to ensure the audio element is rendered
        setTimeout(() => {
          const audioElement = document.querySelector(`[data-message-id="${lastMessage.id}"] audio`)
          if (audioElement) {
            audioElement.play().catch(console.error)
          }
        }, 500)
      }
    }
  }, [messages, autoPlayEnabled])

  const sendMessage = async (messageText = null) => {
    const textToSend = messageText || input.trim()
    if (!textToSend || isLoading) return

    setInput('')
    setIsLoading(true)

    // Add user message
    setMessages(prev => [...prev, { 
      id: Date.now(), 
      text: textToSend, 
      sender: 'user' 
    }])

    try {
      // Send message to Flask backend
      const response = await fetch('http://localhost:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: textToSend
        })
      })

      const result = await response.json()

      if (result.success) {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: result.response,
          audio: result.audio,
          musicGeneration: result.music_generation,
          sender: 'ai',
          success: true
        }])
      } else {
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: `Error: ${result.error}`,
          sender: 'ai',
          success: false
        }])
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: 'Sorry, I\'m having trouble connecting to my backend. Please try again.',
        sender: 'ai',
        success: false
      }])
    } finally {
      setIsLoading(false)
      // Refocus textarea after sending message
      setTimeout(() => {
        textareaRef.current?.focus()
      }, 100)
    }
  }

  const handleVoiceInput = (text) => {
    sendMessage(text)
  }

  const handleAudioRecorded = (audioFile) => {
    // Add audio message to chat
    setMessages(prev => [...prev, {
      id: Date.now(),
      type: 'audio',
      file: audioFile,
      sender: 'user'
    }])

    // TODO: Send audio file to backend for MIDI conversion
    // This will be implemented when the MIDI conversion service is ready
    console.log('Audio file recorded:', audioFile)
    
    // For now, add a placeholder AI response
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        text: 'I received your audio recording! This will be converted to MIDI and imported into Reaper once the conversion service is implemented.',
        sender: 'ai'
      }])
    }, 1000)
  }

  const handleInputChange = (e) => {
    setInput(e.target.value)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const renderMessage = (message) => {
    if (message.type === 'audio') {
      return <AudioMessage file={message.file} sender={message.sender} />
    }
    
    // For AI messages with audio, use AIVoiceResponse
    if (message.sender === 'ai' && message.audio) {
      return (
        <div>
          <AIVoiceResponse 
            text={message.text}
            audioBase64={message.audio}
            messageId={message.id}
            onPlayStart={() => console.log('AI voice started playing')}
            onPlayEnd={() => console.log('AI voice finished playing')}
          />
          {message.musicGeneration && (
            <MusicGenerationResult musicGeneration={message.musicGeneration} />
          )}
        </div>
      )
    }
    
    // For AI messages without audio but with music generation
    if (message.sender === 'ai' && message.musicGeneration) {
      return (
        <div>
          <div>{message.text}</div>
          <MusicGenerationResult musicGeneration={message.musicGeneration} />
        </div>
      )
    }
    
    return message.text
  }

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-4 min-h-0">
        <div className="flex flex-col space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`chat-bubble-${message.sender}`}
            >
              {message.sender === 'user' ? (
                <>
                  <div className="chat-bubble-icon">
                    {message.type === 'audio' ? '🎵' : '👤'}
                  </div>
                  <div className="chat-bubble-content">
                    {renderMessage(message)}
                  </div>
                </>
              ) : (
                <>
                  <div className="chat-bubble-header">
                    <div className="chat-bubble-ai-icon">
                      🤖
                    </div>
                    <div className="chat-bubble-name">
                      DAWZY
                    </div>
                  </div>
                  <div className="chat-bubble-content">
                    {renderMessage(message)}
                  </div>
                </>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="chat-bubble-ai">
              <div className="chat-bubble-header">
                <div className="chat-bubble-ai-icon">
                  🤖
                </div>
                <div className="chat-bubble-name">
                  DAWZY
                </div>
              </div>
              <div className="chat-bubble-content">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-white rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      {/* Input Area - Fixed at bottom */}
      <div className="flex-shrink-0 p-6 pt-2" ref={inputContainerRef}>
        <div className="input-container">
          <div className="relative">
            <textarea
              ref={textareaRef}
              className="custom-textarea pr-20 pb-12"
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here... (Press Enter to send)"
              disabled={isLoading}
              rows={1}
            />
            <div className="absolute bottom-3 right-3 flex items-center gap-2">
              <VoiceButton 
                onVoiceInput={handleVoiceInput}
                disabled={isLoading}
              />
              <RecordButton 
                onAudioRecorded={handleAudioRecorded}
                disabled={isLoading}
              />
            </div>
          </div>
          
          {/* Auto-play Toggle */}
          <div className="mt-2 flex items-center justify-end">
            <button
              onClick={() => setAutoPlayEnabled(!autoPlayEnabled)}
              title={autoPlayEnabled ? 'Turn off AI voice responses' : 'Turn on AI voice responses'}
              className={`
                voice-play-button ${autoPlayEnabled ? 'playing' : ''}
                cursor-pointer
              `}
            >
              {autoPlayEnabled ? '🔊' : '🔇'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ChatWindow 