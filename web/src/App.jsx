import { useState, useEffect, useCallback, useMemo } from 'react'
import Header from './components/Header'
import ClipCard from './components/ClipCard'
import VideoPreview from './components/VideoPreview'
import FilterControls from './components/FilterControls'
import ChapterSelector from './components/ChapterSelector'

const API_BASE = '/api'

function App() {
  const [url, setUrl] = useState('')
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedJob, setExpandedJob] = useState(null)
  const [logs, setLogs] = useState([])
  const [captionStyles, setCaptionStyles] = useState([])
  const [selectedStyle, setSelectedStyle] = useState('default')
  const [aiAvailable, setAiAvailable] = useState(false)
  const [useAi, setUseAi] = useState(false)
  const [sortBy, setSortBy] = useState('recent')
  const [filterStatus, setFilterStatus] = useState('all')
  const [previewVideo, setPreviewVideo] = useState(null)
  const [previewJob, setPreviewJob] = useState(null)
  // Chapter selection state
  const [chapterSelectJob, setChapterSelectJob] = useState(null)
  const [chapters, setChapters] = useState([])
  const [selectedClips, setSelectedClips] = useState(new Set())

  // Fetch data on mount
  useEffect(() => {
    fetchJobs()
    fetchCaptionStyles()
    fetchDetectionModes()
    const interval = setInterval(fetchJobs, 3000)
    return () => clearInterval(interval)
  }, [])

  // Fetch logs when job is expanded
  useEffect(() => {
    if (!expandedJob) {
      setLogs([])
      return
    }
    fetchLogs(expandedJob)
    const interval = setInterval(() => fetchLogs(expandedJob), 2000)
    return () => clearInterval(interval)
  }, [expandedJob])

  // Auto-detect jobs ready for chapter selection
  useEffect(() => {
    const readyJob = jobs.find(j => j.status === 'chapters_ready')
    if (readyJob && readyJob.id !== chapterSelectJob?.id) {
      fetchChapters(readyJob.id)
      setChapterSelectJob(readyJob)
    } else if (!readyJob && chapterSelectJob) {
      // Clear if no more jobs in chapters_ready state
      setChapterSelectJob(null)
      setChapters([])
    }
  }, [jobs, chapterSelectJob])

  const fetchChapters = useCallback(async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/chapters`)
      if (res.ok) {
        const data = await res.json()
        setChapters(data.chapters || [])
      }
    } catch (err) {
      console.error('Failed to fetch chapters:', err)
    }
  }, [])

  const fetchCaptionStyles = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/caption-styles`)
      if (res.ok) {
        const data = await res.json()
        setCaptionStyles(data.styles || [])
      }
    } catch (err) {
      console.error('Failed to fetch caption styles:', err)
    }
  }, [])

  const fetchDetectionModes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/detection-modes`)
      if (res.ok) {
        const data = await res.json()
        setAiAvailable(data.ai_configured || false)
      }
    } catch (err) {
      console.error('Failed to fetch detection modes:', err)
    }
  }, [])

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs`)
      if (res.ok) {
        const data = await res.json()
        setJobs(data.reverse())
      }
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    }
  }, [])

  const fetchLogs = useCallback(async (jobId) => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/logs`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  }, [])

  const submitJob = useCallback(async (e) => {
    e.preventDefault()
    if (!url.trim() || loading) return

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: url.trim(),
          caption_style: selectedStyle,
          auto_detect: true,
          use_ai_detection: useAi
        })
      })
      if (res.ok) {
        setUrl('')
        fetchJobs()
      }
    } catch (err) {
      console.error('Failed to submit job:', err)
    }
    setLoading(false)
  }, [url, loading, selectedStyle, useAi, fetchJobs])

  const deleteJob = useCallback(async (jobId) => {
    try {
      await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' })
      if (expandedJob === jobId) setExpandedJob(null)
      fetchJobs()
    } catch (err) {
      console.error('Failed to delete job:', err)
    }
  }, [expandedJob, fetchJobs])

  const getStatusLabel = (status) => {
    const labels = {
      pending: '⏳ Pending',
      downloading: '⬇️ Downloading',
      transcribing: '🎧 Transcribing',
      analyzing: '🧠 Analyzing',
      chapters_ready: '📚 Select Chapters',
      processing: '✂️ Processing',
      completed: '✅ Completed',
      failed: '❌ Failed'
    }
    return labels[status] || status
  }

  const formatETA = useCallback((seconds) => {
    if (!seconds || seconds <= 0) return null
    if (seconds < 60) return `~${seconds}s remaining`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `~${mins}m ${secs}s remaining`
  }, [])

  // Filtered and sorted jobs
  const filteredAndSortedJobs = useMemo(() => {
    let filtered = jobs

    if (filterStatus !== 'all') {
      filtered = filtered.filter(job => job.status === filterStatus)
    }

    const sorted = [...filtered]
    switch (sortBy) {
      case 'recent':
        break
      case 'oldest':
        sorted.reverse()
        break
      case 'completed':
        sorted.sort((a, b) => {
          if (a.status === 'completed' && b.status !== 'completed') return -1
          if (a.status !== 'completed' && b.status === 'completed') return 1
          return 0
        })
        break
      case 'score':
        sorted.sort((a, b) => {
          const aMaxScore = Math.max(...(a.clips || []).map(c => c.score || 0), 0)
          const bMaxScore = Math.max(...(b.clips || []).map(c => c.score || 0), 0)
          return bMaxScore - aMaxScore
        })
        break
      default:
        break
    }

    return sorted
  }, [jobs, filterStatus, sortBy])



  const toggleClipSelection = useCallback((jobId, clip) => {
    setSelectedClips(prev => {
      const next = new Set(prev)
      const clipId = `${jobId}_${clip.filename}` // Unique value
      const existing = Array.from(next).find(c => c.id === clipId)
      
      if (existing) {
        next.delete(existing)
      } else {
        next.add({
          id: clipId,
          jobId,
          filename: clip.filename,
          url: `${API_BASE}/jobs/${jobId}/download?filename=${clip.filename}`
        })
      }
      return next
    })
  }, [])

  const downloadSelected = useCallback(() => {
    selectedClips.forEach((clip, index) => {
      setTimeout(() => {
        window.open(clip.url, '_blank')
      }, index * 500) // Stagger downloads
    })
    // Optional: Clear selection after download?
    // setSelectedClips(new Set())
  }, [selectedClips])

  const handleChapterSubmit = useCallback(() => {
    setChapterSelectJob(null)
    setChapters([])
    fetchJobs() // Refresh to see processing status
  }, [fetchJobs])

  const handleChapterCancel = useCallback(() => {
    if(!chapterSelectJob) return
    // Maybe we want to keep it in the list but close the modal
    // For now, just close the modal
    setChapterSelectJob(null)
    setChapters([])
  }, [chapterSelectJob])

  return (
    <div className="min-h-screen px-4 py-8 max-w-7xl mx-auto">
      <Header />
      
      {/* Chapter Selector Modal */}
      {chapterSelectJob && (
         <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
            <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
               <ChapterSelector 
                  jobId={chapterSelectJob.id}
                  chapters={chapters}
                  onSubmit={handleChapterSubmit}
                  onCancel={handleChapterCancel}
               />
            </div>
         </div>
      )}

      {/* Batch Download Button */}
      {selectedClips.size > 0 && (
         <div className="fixed bottom-8 right-8 z-40">
            <button 
               onClick={downloadSelected}
               className="btn-primary px-6 py-4 rounded-full shadow-2xl flex items-center gap-3 text-lg animate-bounce-subtle"
            >
               <span>⬇️</span>
               <span>Download ({selectedClips.size})</span>
            </button>
         </div>
      )}

      {/* Submit Form */}
      <div className="card p-8 mb-12 hover:shadow-2xl hover:shadow-accent/10">
        <form onSubmit={submitJob} className="space-y-6">
          <div className="flex gap-4 flex-col sm:flex-row">
            <input
              type="text"
              placeholder="Paste YouTube URL here..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
              className="flex-1 bg-dark-800 border-2 border-gray-700 rounded-xl px-6 py-4 text-lg focus:border-accent focus:outline-none transition-all"
            />
            <select
              value={selectedStyle}
              onChange={(e) => setSelectedStyle(e.target.value)}
              disabled={loading}
              className="bg-dark-800 border-2 border-gray-700 rounded-xl px-6 py-4 focus:border-accent focus:outline-none transition-colors min-w-[200px]"
            >
              {captionStyles.map(style => (
                <option key={style.id} value={style.id}>{style.name}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="btn-primary whitespace-nowrap px-8 py-4 text-lg"
            >
              {loading ? 'Submitting...' : 'Create Clip'}
            </button>
          </div>

          <div className="flex items-center justify-center">
            <label className="flex items-center gap-3 cursor-pointer px-4 py-2 rounded-lg hover:bg-dark-800 transition-colors">
              <input
                type="checkbox"
                checked={useAi}
                onChange={(e) => setUseAi(e.target.checked)}
                disabled={!aiAvailable || loading}
                className="w-5 h-5 accent-accent"
              />
              <span className="text-gray-300 font-medium">🤖 Use AI Detection</span>
              {!aiAvailable && (
                <span className="text-xs text-gray-500">(Add API key in .env)</span>
              )}
            </label>
          </div>

          <p className="text-center text-sm text-gray-500">
            {useAi && aiAvailable ? '🤖 AI-powered detection (Gemini/OpenAI)' : '📊 Rule-based detection (free)'} • 🎨 Caption: {captionStyles.find(s => s.id === selectedStyle)?.name || 'Default'}
          </p>
        </form>
      </div>

      {/* Jobs Section */}
      <section>
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <h2 className="text-3xl font-bold">Your Clips</h2>
          {jobs.length > 0 && (
            <FilterControls
              filterStatus={filterStatus}
              setFilterStatus={setFilterStatus}
              sortBy={sortBy}
              setSortBy={setSortBy}
            />
          )}
        </div>

        {jobs.length === 0 ? (
          <div className="card p-16 text-center">
            <p className="text-xl text-gray-500">
              No clips yet. Paste a YouTube URL above to get started!
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredAndSortedJobs.map(job => (
              <div key={job.id} className="card p-6">
                <div className="flex items-start gap-6 flex-col lg:flex-row">
                  {/* Job Info */}
                  <div className="flex-1 space-y-3">
                    <div className="text-sm text-gray-500 truncate">{job.url}</div>

                    <div className="flex items-center gap-3 flex-wrap">
                      <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm ${
                        job.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        job.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {['downloading', 'transcribing', 'processing'].includes(job.status) && (
                          <span className="animate-spin">⚙️</span>
                        )}
                        {getStatusLabel(job.status)}
                        {job.eta_seconds && (
                          <span className="text-xs opacity-75">• {formatETA(job.eta_seconds)}</span>
                        )}
                      </span>
                    </div>

                    {job.status !== 'completed' && job.status !== 'failed' && (
                      <div className="w-full bg-dark-800 rounded-full h-2 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-accent to-pink-500 h-full transition-all duration-500 shadow-lg shadow-accent/50"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    )}

                    {/* Logs */}
                    <button
                      onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                      className="text-sm text-gray-500 hover:text-accent transition-colors"
                    >
                      {expandedJob === job.id ? '▼ Hide Logs' : '▶ Show Logs'}
                    </button>

                    {expandedJob === job.id && (
                      <div className="bg-dark-900 border border-gray-800 rounded-xl p-4 max-h-48 overflow-y-auto font-mono text-xs text-gray-400 space-y-1">
                        {logs.length === 0 ? (
                          <div>Waiting for logs...</div>
                        ) : (
                          logs.map((line, i) => <div key={i}>{line}</div>)
                        )}
                      </div>
                    )}

                    {job.error && (
                      <div className="text-red-400 text-sm bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                        {job.error}
                      </div>
                    )}
                  </div>

                  {/* Clips Grid or Delete Button */}
                  <div className="flex gap-4 items-start">
                    {job.status === 'completed' && job.clips && job.clips.length > 0 && (
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {job.clips.map((clip, idx) => {
                           const clipId = `${job.id}_${clip.filename}`;
                           const isSelected = Array.from(selectedClips).some(c => c.id === clipId);
                           
                           return (
                              <ClipCard
                                key={idx}
                                clip={{...clip, isSelected}}
                                jobId={job.id}
                                onPreview={(clip) => {
                                  setPreviewVideo(clip)
                                  setPreviewJob(job.id)
                                }}
                                onToggleSelect={() => toggleClipSelection(job.id, clip)}
                              />
                           )
                        })}
                      </div>
                    )}

                    <button
                      onClick={() => deleteJob(job.id)}
                      className="p-3 rounded-xl border-2 border-gray-700 hover:border-red-500 hover:bg-red-500 hover:scale-110 transition-all text-xl"
                      title="Delete job"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Video Preview Modal */}
      {previewVideo && (
        <VideoPreview
          clip={previewVideo}
          jobId={previewJob}
          onClose={() => setPreviewVideo(null)}
        />
      )}
    </div>
  )
}

export default App
