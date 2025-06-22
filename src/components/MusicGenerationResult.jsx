import React from 'react'

const MusicGenerationResult = ({ musicGeneration }) => {
  if (!musicGeneration || !musicGeneration.success) {
    return null
  }

  const { structured_instructions, message, file_path } = musicGeneration

  return (
    <div className="music-generation-result mt-4 p-4 bg-gradient-to-r from-purple-900/50 to-pink-900/50 border border-purple-500/30 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-white font-semibold">Generated Music Track</h3>
      </div>
      
      <div className="text-sm text-white/80 mb-3">
        <p className="mb-2">{message}</p>
      </div>

      {structured_instructions && (
        <div className="bg-black/20 rounded p-3 mb-3">
          <h4 className="text-white font-medium mb-2">Track Details:</h4>
          <div className="grid grid-cols-2 gap-2 text-xs text-white/70">
            <div>
              <span className="font-medium">Genre:</span> {structured_instructions.genre || 'N/A'}
            </div>
            <div>
              <span className="font-medium">Tempo:</span> {structured_instructions.tempo || 'N/A'} BPM
            </div>
            <div>
              <span className="font-medium">Key:</span> {structured_instructions.key || 'N/A'}
            </div>
            <div>
              <span className="font-medium">Mood:</span> {structured_instructions.mood || 'N/A'}
            </div>
            <div className="col-span-2">
              <span className="font-medium">Duration:</span> {structured_instructions.duration || 'N/A'} seconds
            </div>
            {structured_instructions.instruments && (
              <div className="col-span-2">
                <span className="font-medium">Instruments:</span> {structured_instructions.instruments.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-green-400">
        <span>✅</span>
        <span>Track imported into REAPER</span>
      </div>
    </div>
  )
}

export default MusicGenerationResult 