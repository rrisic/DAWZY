import ChatWindow from './components/ChatWindow'

export default function App() {
  return (
    <div className="w-full h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-pink-900 flex items-center justify-center p-4">
      <div className="w-full h-full max-w-2xl flex items-center justify-center">
        <ChatWindow />
      </div>
    </div>
  )
} 