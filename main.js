const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow
let pythonProcess = null

// Disable GPU acceleration to prevent GPU process crashes
app.disableHardwareAcceleration()

// Handle GPU process crashes gracefully
app.commandLine.appendSwitch('--disable-gpu-sandbox')
app.commandLine.appendSwitch('--disable-software-rasterizer')
app.commandLine.appendSwitch('--disable-dev-shm-usage')
app.commandLine.appendSwitch('--no-sandbox')

function createWindow () {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 1000,
    minHeight: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      // Disable hardware acceleration for renderer
      enableRemoteModule: false,
      webSecurity: true,
      // Disable hardware acceleration
      offscreen: false
    },
    // Make it look more professional for demos
    titleBarStyle: 'default',
    show: false, // Don't show until ready
    icon: path.join(__dirname, 'assets/icon.png'), // Optional: add an icon
    // Prevent flashing
    backgroundColor: '#2e026d' // Match the gradient background
  })

  // Load the built React app
  const isDev = process.env.NODE_ENV === 'development'
  if (isDev) {
    mainWindow.loadURL('http://localhost:5174')
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist/index.html'))
  }

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    // Focus the window
    mainWindow.focus()
  })

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Handle GPU process crashes
  mainWindow.webContents.on('crashed', (event, killed) => {
    console.log('Renderer process crashed:', killed)
    // Reload the window if it crashes
    if (!killed) {
      mainWindow.reload()
    }
  })

  // Optional: Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools()
  }
}

function startPythonBackend() {
  // Start Python backend process
  const pythonPath = process.platform === 'win32' ? 'python' : 'python3'
  pythonProcess = spawn(pythonPath, ['backend/app.py'], {
    stdio: ['pipe', 'pipe', 'pipe'],
    cwd: __dirname
  })

  pythonProcess.stdout.on('data', (data) => {
    console.log('Python backend:', data.toString())
  })

  pythonProcess.stderr.on('data', (data) => {
    console.error('Python backend error:', data.toString())
  })

  pythonProcess.on('close', (code) => {
    console.log('Python backend process exited with code:', code)
    // Try to restart the backend if it crashes
    if (mainWindow && !app.isQuitting) {
      setTimeout(startPythonBackend, 2000)
    }
  })

  pythonProcess.on('error', (error) => {
    console.error('Failed to start Python backend:', error)
  })
}

// IPC handlers for communication with renderer process
ipcMain.handle('send-to-backend', async (event, message) => {
  if (!pythonProcess) {
    throw new Error('Python backend not running')
  }

  return new Promise((resolve, reject) => {
    // Set up response listener
    const responseHandler = (data) => {
      try {
        const response = JSON.parse(data.toString())
        if (response.type === 'response') {
          pythonProcess.stdout.removeListener('data', responseHandler)
          resolve({
            reply: response.content,
            success: response.success,
            actions: response.actions || []
          })
        }
      } catch (e) {
        // Not a JSON response, ignore
      }
    }

    pythonProcess.stdout.on('data', responseHandler)

    // Send message to Python backend via stdin
    try {
      pythonProcess.stdin.write(JSON.stringify({ type: 'message', content: message }) + '\n')
      
      // Timeout after 10 seconds
      setTimeout(() => {
        pythonProcess.stdout.removeListener('data', responseHandler)
        reject(new Error('Backend response timeout'))
      }, 10000)
    } catch (error) {
      pythonProcess.stdout.removeListener('data', responseHandler)
      reject(error)
    }
  })
})

ipcMain.handle('send-voice-to-backend', async (event, audioData) => {
  if (!pythonProcess) {
    throw new Error('Python backend not running')
  }

  // Send voice data to Python backend
  pythonProcess.stdin.write(JSON.stringify({ type: 'voice', content: audioData }) + '\n')
  
  return {
    reply: '🎤 Voice processing will be implemented soon!'
  }
})

ipcMain.handle('get-backend-status', async () => {
  return {
    connected: pythonProcess !== null && !pythonProcess.killed,
    pid: pythonProcess ? pythonProcess.pid : null
  }
})

// App lifecycle
app.whenReady().then(() => {
  createWindow()
  startPythonBackend()
})

// Handle GPU process crashes at app level
app.on('gpu-process-crashed', (event, killed) => {
  console.log('GPU process crashed:', killed)
  // Don't quit the app, just log the crash
})

// Handle renderer process crashes at app level
app.on('render-process-gone', (event, webContents, details) => {
  console.log('Renderer process gone:', details.reason)
  if (details.reason === 'crashed' && mainWindow) {
    mainWindow.reload()
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})

app.on('before-quit', () => {
  app.isQuitting = true
  if (pythonProcess) {
    pythonProcess.kill()
  }
})

// Handle app quit
process.on('exit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
})

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error)
  // Don't quit the app for uncaught exceptions
})

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason)
  // Don't quit the app for unhandled rejections
}) 