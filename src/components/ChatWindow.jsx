import React, { useState, useEffect, useRef } from 'react'

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

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setIsLoading(true)

    // Add user message
    setMessages(prev => [...prev, { 
      id: Date.now(), 
      text: userMessage, 
      sender: 'user' 
    }])

    try {
      // Send message to Python backend
      const response = await window.musicAssistant.sendMessage(userMessage)
      
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

  const handleInputChange = (e) => {
    setInput(e.target.value)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-transparent">
      {/* Chat Messages Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-6 pb-4 pt-6">
        <div className="flex flex-col space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`chat-bubble-${message.sender}`}
            >
              {message.sender === 'user' ? (
                <>
                  <div className="chat-bubble-icon">
                    👤
                  </div>
                  <div className="chat-bubble-content">
                    {message.text}
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
                    {message.text}
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
      <div className="p-6 pt-2" ref={inputContainerRef}>
        <div className="input-container">
          <textarea
            ref={textareaRef}
            className="custom-textarea"
            value={input}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here... (Press Enter to send)"
            disabled={isLoading}
            rows={1}
          />
        </div>
      </div>
    </div>
  )
}

export default ChatWindow 