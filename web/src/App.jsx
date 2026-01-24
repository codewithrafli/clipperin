import { useState, useEffect, useCallback, useMemo } from 'react'

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
  const [sortBy, setSortBy] = useState('recent') // new: sorting
  const [filterStatus, setFilterStatus] = useState('all') // new: filtering

  // Fetch jobs and caption styles on mount
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
        setJobs(data.reverse()) // newest first
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

  const downloadJob = useCallback((jobId) => {
    window.open(`${API_BASE}/jobs/${jobId}/download?filename=output.mp4`, '_blank')
  }, [])

  function getStatusLabel(status) {
    const labels = {
      pending: '⏳ Pending',
      downloading: '⬇️ Downloading',
      transcribing: '🎧 Transcribing',
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

  // Filtered and sorted jobs (memoized for performance)
  const filteredAndSortedJobs = useMemo(() => {
    let filtered = jobs

    // Apply status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(job => job.status === filterStatus)
    }

    // Apply sorting
    const sorted = [...filtered]
    switch (sortBy) {
      case 'recent':
        // Already sorted by newest first from API
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

  return (
    <div className="container">
      <header className="header">
        <h1>🎬 Auto Clipper</h1>
        <p>Transform long videos into viral short clips</p>
        <span className="badge">✨ No recurring fees - 100% offline</span>
      </header>

      <form className="submit-form" onSubmit={submitJob}>
        <div className="input-group">
          <input
            type="text"
            placeholder="Paste YouTube URL here..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
          />
          <select 
            className="style-select"
            value={selectedStyle}
            onChange={(e) => setSelectedStyle(e.target.value)}
            disabled={loading}
          >
            {captionStyles.map(style => (
              <option key={style.id} value={style.id}>{style.name}</option>
            ))}
          </select>
          <button type="submit" className="btn" disabled={loading || !url.trim()}>
            {loading ? 'Submitting...' : 'Create Clip'}
          </button>
        </div>
        <div className="form-options">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={useAi}
              onChange={(e) => setUseAi(e.target.checked)}
              disabled={!aiAvailable || loading}
            />
            <span>🤖 Use AI Detection</span>
            {!aiAvailable && <span className="hint">(Add API key in .env)</span>}
          </label>
        </div>
        <div className="form-hint">
          {useAi && aiAvailable ? '🤖 AI-powered detection (Gemini/OpenAI)' : '📊 Rule-based detection (free)'} • 🎨 Caption: {captionStyles.find(s => s.id === selectedStyle)?.name || 'Default'}
        </div>
      </form>

      <section className="jobs-section">
        <div className="section-header">
          <h2>Your Clips</h2>
          {jobs.length > 0 && (
            <div className="controls">
              <select
                className="filter-select"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
              <select
                className="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest First</option>
                <option value="completed">Completed First</option>
                <option value="score">Highest Score</option>
              </select>
            </div>
          )}
        </div>

        {jobs.length === 0 ? (
          <div className="empty-state">
            <p>No clips yet. Paste a YouTube URL above to get started!</p>
          </div>
        ) : (
          <div className="jobs-list">
            {filteredAndSortedJobs.map(job => (
              <div key={job.id} className="job-card">
                <div className="job-info">
                  <div className="job-url">{job.url}</div>
                  <div className={`job-status status-${job.status}`}>
                    {['downloading', 'transcribing', 'processing'].includes(job.status) && (
                      <span className="spinner" />
                    )}
                    {getStatusLabel(job.status)}
                    {job.eta_seconds && (
                      <span className="eta"> • {formatETA(job.eta_seconds)}</span>
                    )}
                  </div>
                  {job.status !== 'completed' && job.status !== 'failed' && (
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{ width: `${job.progress}%` }} 
                      />
                    </div>
                  )}
                  
                  {/* Logs toggle button */}
                  <button 
                    className="btn-logs"
                    onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
                  >
                    {expandedJob === job.id ? '▼ Hide Logs' : '▶ Show Logs'}
                  </button>
                  
                  {/* Logs display */}
                  {expandedJob === job.id && (
                    <div className="logs-panel">
                      {logs.length === 0 ? (
                        <div className="log-line">Waiting for logs...</div>
                      ) : (
                        logs.map((line, i) => (
                          <div key={i} className="log-line">{line}</div>
                        ))
                      )}
                    </div>
                  )}
                  
                  {job.error && (
                    <div style={{ color: 'var(--error)', fontSize: '0.75rem', marginTop: '0.5rem' }}>
                      {job.error}
                    </div>
                  )}
                </div>
                <div className="job-actions">
                  {job.status === 'completed' && (
                    <div className="clips-grid">
                      {job.clips && job.clips.length > 0 ? (
                        job.clips.map((clip, idx) => (
                           <div key={idx} className="clip-item">
                              {clip.thumbnail && (
                                <div className="clip-thumbnail">
                                  <img
                                    src={`${API_BASE}/jobs/${job.id}/thumbnail/${clip.thumbnail}`}
                                    alt={`Clip ${idx+1}`}
                                    loading="lazy"
                                  />
                                </div>
                              )}
                              <div className="clip-header">
                                <span className="clip-score">🔥 {clip.score}/10</span>
                                <span className="clip-duration">~{30}s</span>
                              </div>
                              <div className="clip-title" title={clip.hook}>
                                {clip.hook || `Viral Clip #${idx+1}`}
                              </div>
                              <button
                                className="btn-download-small"
                                onClick={() => window.open(`${API_BASE}/jobs/${job.id}/download?filename=${clip.filename}`, '_blank')}
                              >
                                ⬇ Download
                              </button>
                           </div>
                        ))
                      ) : (
                        <button
                          className="btn btn-download"
                          onClick={() => downloadJob(job.id)}
                        >
                          Download Clip
                        </button>
                      )}
                    </div>
                  )}
                  <button 
                    className="btn btn-delete" 
                    onClick={() => deleteJob(job.id)}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default App
