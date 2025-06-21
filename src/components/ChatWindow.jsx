import React, { useState, useEffect, useRef } from 'react'
import VoiceButton from './VoiceButton'
import RecordButton from './RecordButton'
import AudioMessage from './AudioMessage'

const ChatWindow = () => {
  const [messages, setMessages] = useState([
    { id: 1, sender: 'ai', text: 'Hi! I\'m your music production assistant. How can I help you today?' }
  ])
  const [input, setInput] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const inputContainerRef = useRef(null)

  useEffect(() => {
    // Check backend connection status
    const checkConnection = async () => {
      try {
        const status = await window.musicAssistant.getConnectionStatus()
        setIsConnected(status.connected)
      } catch (error) {
        console.error('Failed to check connection:', error)
        setIsConnected(false)
      }
    }
    
    checkConnection()
    const interval = setInterval(checkConnection, 5000) // Check every 5 seconds
    
    return () => clearInterval(interval)
  }, [])

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
      // Send message to Python backend
      const response = await window.musicAssistant.sendMessage(textToSend)
      
      setMessages(prev => [...prev, response])
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
          <div className="flex items-end gap-3">
            <textarea
              ref={textareaRef}
              className="custom-textarea flex-1"
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here... (Press Enter to send)"
              disabled={isLoading}
              rows={1}
            />
            <div className="flex items-center gap-2">
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
        </div>
      </div>
    </div>
  )
}

export default ChatWindow 