const API_BASE = '/api'

export default function ClipCard({ clip, jobId, onPreview, onToggleSelect }) {
  const handleDownload = () => {
    window.open(`${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`, '_blank')
  }

  return (
    <div className="card card-hover overflow-hidden group">
      {/* Thumbnail */}
      <div className="relative aspect-[9/16] bg-gradient-to-br from-purple-900/20 to-pink-900/20 overflow-hidden">
        {clip.thumbnail ? (
          <img
            src={`${API_BASE}/jobs/${jobId}/thumbnail/${clip.thumbnail}`}
            alt="Clip thumbnail"
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-6xl opacity-30">🎬</span>
          </div>
        )}

        {/* Hover Preview Button */}
        <button
          onClick={() => onPreview(clip)}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        >
          <div className="bg-white/20 backdrop-blur-md border-2 border-white/30 px-6 py-3 rounded-full text-white font-semibold hover:bg-accent hover:border-accent transition-all">
            ▶️ Preview
          </div>
        </button>


        {/* Selection Checkbox */}
        <div className="absolute top-2 left-2 z-10">
          <input
             type="checkbox"
             checked={clip.isSelected}
             onChange={() => onToggleSelect(clip)}
             className="w-5 h-5 accent-accent cursor-pointer shadow-lg"
             onClick={(e) => e.stopPropagation()} 
          />
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Score & Duration */}
        <div className="flex items-center justify-between text-sm">
          <span className="bg-gradient-to-r from-green-500 to-emerald-500 bg-clip-text text-transparent font-bold text-lg">
            🔥 {clip.score}/10
          </span>
          <span className="text-gray-500">~30s</span>
        </div>

        {/* Hook Text */}
        <p className="text-sm font-medium text-gray-300 line-clamp-2 min-h-[2.5rem]">
          {clip.hook || `Viral Clip`}
        </p>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => onPreview(clip)}
            className="flex-1 btn-secondary text-sm py-2"
          >
            👁️ Preview
          </button>
          <button
            onClick={handleDownload}
            className="flex-1 btn-primary text-sm py-2"
          >
            ⬇️ Download
          </button>
        </div>
      </div>
    </div>
  )
}
