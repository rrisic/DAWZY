const { contextBridge, ipcRenderer } = require('electron')

// Expose a safe API for communicating with Python backend
contextBridge.exposeInMainWorld('musicAssistant', {
  // Send message to Python backend and get response
  sendMessage: async (message) => {
    try {
      // Send message to main process, which will forward to Python backend
      const response = await ipcRenderer.invoke('send-to-backend', message)
      return {
        sender: 'ai',
        text: response.reply,
        success: true
      }
    } catch (error) {
      return {
        sender: 'ai',
        text: 'Sorry, I\'m having trouble connecting to my backend. Please try again.',
        success: false,
        error: error.message
      }
    }
  },

  // Future: Send voice data to Python backend
  sendVoice: async (audioData) => {
    try {
      const response = await ipcRenderer.invoke('send-voice-to-backend', audioData)
      return {
        sender: 'ai',
        text: response.reply,
        success: true
      }
    } catch (error) {
      return {
        sender: 'ai',
        text: 'Sorry, I couldn\'t process your voice input.',
        success: false,
        error: error.message
      }
    }
  },

  // Get connection status
  getConnectionStatus: () => ipcRenderer.invoke('get-backend-status'),

  // Save audio recording to local machine
  saveAudioRecording: async (audioBlob, filename) => {
    try {
      console.log('Preload: Starting saveAudioRecording')
      const arrayBuffer = await audioBlob.arrayBuffer()
      const buffer = Buffer.from(arrayBuffer)
      console.log('Preload: Calling save-audio-file IPC')
      const response = await ipcRenderer.invoke('save-audio-file', buffer, filename)
      console.log('Preload: IPC response received:', response)
      return {
        success: true,
        filePath: response.filePath,
        filename: response.filename
      }
    } catch (error) {
      console.error('Preload: Error in saveAudioRecording:', error)
      return {
        success: false,
        error: error.message
      }
    }
  }
}) 