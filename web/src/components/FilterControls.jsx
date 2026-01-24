export default function FilterControls({ filterStatus, setFilterStatus, sortBy, setSortBy }) {
  return (
    <div className="flex gap-3 flex-wrap">
      <select
        value={filterStatus}
        onChange={(e) => setFilterStatus(e.target.value)}
        className="bg-dark-800 border-2 border-gray-700 rounded-xl px-4 py-2 text-sm focus:border-accent focus:outline-none transition-colors"
      >
        <option value="all">All Status</option>
        <option value="completed">Completed</option>
        <option value="processing">Processing</option>
        <option value="failed">Failed</option>
      </select>

      <select
        value={sortBy}
        onChange={(e) => setSortBy(e.target.value)}
        className="bg-dark-800 border-2 border-gray-700 rounded-xl px-4 py-2 text-sm focus:border-accent focus:outline-none transition-colors"
      >
        <option value="recent">Most Recent</option>
        <option value="oldest">Oldest First</option>
        <option value="completed">Completed First</option>
        <option value="score">Highest Score</option>
      </select>
    </div>
  )
}
