const API_BASE = '/api'

export default function VideoPreview({ clip, jobId, onClose }) {
  if (!clip) return null

  const handleDownload = () => {
    window.open(`${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`, '_blank')
  }

  return (
    <div
      className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-dark-700 border border-gray-800 rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <h3 className="text-2xl font-bold">🎬 Preview Clip</h3>
          <button
            onClick={onClose}
            className="w-12 h-12 rounded-full border-2 border-gray-700 hover:border-red-500 hover:bg-red-500 hover:rotate-90 transition-all duration-300 flex items-center justify-center text-xl"
          >
            ✕
          </button>
        </div>

        {/* Video Player */}
        <div className="p-6 space-y-6">
          <video
            key={clip.filename}
            controls
            autoPlay
            className="w-full aspect-[9/16] bg-black rounded-2xl"
            src={`${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`}
          >
            Your browser does not support video playback.
          </video>

          {/* Info */}
          <div className="space-y-4">
            {/* Badges */}
            <div className="flex gap-3 flex-wrap">
              <div className="bg-dark-800 border border-gray-700 px-4 py-2 rounded-xl">
                <span className="bg-gradient-to-r from-green-500 to-emerald-500 bg-clip-text text-transparent font-bold">
                  🔥 Score: {clip.score}/10
                </span>
              </div>
              <div className="bg-dark-800 border border-gray-700 px-4 py-2 rounded-xl text-gray-400">
                ⏱️ ~30s
              </div>
            </div>

            {/* Hook */}
            <div className="bg-dark-800 border border-gray-700 p-4 rounded-xl">
              <p className="text-gray-400">
                <strong className="text-white">Hook:</strong> {clip.hook || 'N/A'}
              </p>
            </div>

            {/* Download Button */}
            <button
              onClick={handleDownload}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-4 rounded-xl font-semibold hover:shadow-lg hover:shadow-green-500/30 transition-all hover:-translate-y-0.5"
            >
              ⬇️ Download Clip
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
