import { useState, useEffect } from 'react'

const API_BASE = '/api'

function App() {
  const [url, setUrl] = useState('')
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedJob, setExpandedJob] = useState(null)
  const [logs, setLogs] = useState([])

  // Fetch jobs on mount and poll for updates
  useEffect(() => {
    fetchJobs()
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

  async function fetchJobs() {
    try {
      const res = await fetch(`${API_BASE}/jobs`)
      if (res.ok) {
        const data = await res.json()
        setJobs(data.reverse()) // newest first
      }
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    }
  }

  async function fetchLogs(jobId) {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/logs`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    }
  }

  async function submitJob(e) {
    e.preventDefault()
    if (!url.trim() || loading) return

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() })
      })
      if (res.ok) {
        setUrl('')
        fetchJobs()
      }
    } catch (err) {
      console.error('Failed to submit job:', err)
    }
    setLoading(false)
  }

  async function deleteJob(jobId) {
    try {
      await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' })
      if (expandedJob === jobId) setExpandedJob(null)
      fetchJobs()
    } catch (err) {
      console.error('Failed to delete job:', err)
    }
  }

  function downloadJob(jobId) {
    window.open(`${API_BASE}/jobs/${jobId}/download`, '_blank')
  }

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

  function formatETA(seconds) {
    if (!seconds || seconds <= 0) return null
    if (seconds < 60) return `~${seconds}s remaining`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `~${mins}m ${secs}s remaining`
  }

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
          <button type="submit" className="btn" disabled={loading || !url.trim()}>
            {loading ? 'Submitting...' : 'Create Clip'}
          </button>
        </div>
      </form>

      <section className="jobs-section">
        <h2>Your Clips</h2>
        
        {jobs.length === 0 ? (
          <div className="empty-state">
            <p>No clips yet. Paste a YouTube URL above to get started!</p>
          </div>
        ) : (
          <div className="jobs-list">
            {jobs.map(job => (
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
                    <button 
                      className="btn btn-download" 
                      onClick={() => downloadJob(job.id)}
                    >
                      Download
                    </button>
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
