import { useState, useCallback } from 'react'

const API_BASE = '/api'

export default function ChapterSelector({
  jobId,
  chapters,
  onSubmit,
  onCancel
}) {
  const [selected, setSelected] = useState(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const toggleChapter = useCallback((chapterId) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(chapterId)) {
        next.delete(chapterId)
      } else {
        next.add(chapterId)
      }
      return next
    })
  }, [])

  const selectAll = useCallback(() => {
    setSelected(new Set(chapters.map(ch => ch.id)))
  }, [chapters])

  const selectNone = useCallback(() => {
    setSelected(new Set())
  }, [])

  const handleSubmit = useCallback(async () => {
    if (selected.size === 0) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/select-chapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chapter_ids: Array.from(selected)
        })
      })

      if (res.ok) {
        onSubmit()
      } else {
        const data = await res.json()
        setError(data.detail || 'Failed to submit chapters')
      }
    } catch (err) {
      console.error('Failed to submit chapters:', err)
      setError('Network error. Please try again.')
    }

    setLoading(false)
  }, [jobId, selected, onSubmit])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    if (mins > 0) {
      return `${mins}m ${secs}s`
    }
    return `${secs}s`
  }

  // Calculate total selected duration
  const totalDuration = chapters
    .filter(ch => selected.has(ch.id))
    .reduce((sum, ch) => sum + ch.duration, 0)

  return (
    <div className="bg-dark-800 border border-gray-700 rounded-2xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">
            Select Chapters to Clip
          </h3>
          <p className="text-sm text-gray-400 mt-1">
            Choose which chapters to convert into video clips
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={selectAll}
            className="text-sm px-3 py-1.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
          >
            Select All
          </button>
          <button
            onClick={selectNone}
            className="text-sm px-3 py-1.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Selection Summary */}
      {selected.size > 0 && (
        <div className="bg-accent/10 border border-accent/30 rounded-xl px-4 py-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-accent">
              {selected.size} chapter{selected.size !== 1 ? 's' : ''} selected
            </span>
            <span className="text-gray-400">
              Total duration: {formatDuration(totalDuration)}
            </span>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Chapter List */}
      <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {chapters.map((chapter, index) => (
          <div
            key={chapter.id}
            onClick={() => toggleChapter(chapter.id)}
            className={`
              p-4 rounded-xl border-2 cursor-pointer transition-all
              ${selected.has(chapter.id)
                ? 'border-accent bg-accent/5'
                : 'border-gray-700 hover:border-gray-600 bg-dark-700/50'
              }
            `}
          >
            <div className="flex items-start gap-4">
              {/* Checkbox */}
              <div className={`
                w-6 h-6 rounded-lg border-2 flex items-center justify-center flex-shrink-0 mt-0.5
                transition-colors
                ${selected.has(chapter.id)
                  ? 'border-accent bg-accent text-white'
                  : 'border-gray-600'
                }
              `}>
                {selected.has(chapter.id) && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>

              {/* Chapter Info */}
              <div className="flex-1 min-w-0 space-y-2">
                {/* Title Row */}
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-xs font-medium text-gray-500 bg-dark-600 px-2 py-0.5 rounded">
                    #{index + 1}
                  </span>
                  <span className="font-semibold text-white truncate">
                    {chapter.title}
                  </span>
                </div>

                {/* Time Info */}
                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <span className="flex items-center gap-1">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {formatTime(chapter.start)} - {formatTime(chapter.end)}
                  </span>
                  <span className="text-accent font-medium">
                    {formatDuration(chapter.duration)}
                  </span>
                </div>

                {/* Summary */}
                {chapter.summary && (
                  <p className="text-sm text-gray-400 line-clamp-2">
                    {chapter.summary}
                  </p>
                )}

                {/* Keywords */}
                {chapter.keywords && chapter.keywords.length > 0 && (
                  <div className="flex gap-2 flex-wrap">
                    {chapter.keywords.map((kw, i) => (
                      <span
                        key={i}
                        className="text-xs bg-dark-600 px-2 py-1 rounded-full text-gray-400"
                      >
                        #{kw}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Confidence Badge */}
              {chapter.confidence && (
                <div className={`
                  px-2 py-1 rounded-lg text-xs font-medium flex-shrink-0
                  ${chapter.confidence >= 0.8 ? 'bg-green-500/20 text-green-400' :
                    chapter.confidence >= 0.5 ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-gray-500/20 text-gray-400'}
                `}>
                  {Math.round(chapter.confidence * 100)}%
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-4 pt-2">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-3 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-xl font-medium transition-colors"
          disabled={loading}
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={selected.size === 0 || loading}
          className={`
            flex-1 px-4 py-3 rounded-xl font-medium transition-all
            ${selected.size === 0 || loading
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-gradient-to-r from-accent to-pink-500 hover:from-accent/90 hover:to-pink-500/90 text-white shadow-lg shadow-accent/25'
            }
          `}
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Processing...
            </span>
          ) : (
            `Create ${selected.size} Clip${selected.size !== 1 ? 's' : ''}`
          )}
        </button>
      </div>
    </div>
  )
}
