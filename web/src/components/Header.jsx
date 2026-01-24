export default function Header() {
  return (
    <header className="text-center py-12 mb-8">
      <h1 className="text-6xl font-extrabold mb-4 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-500 bg-clip-text text-transparent">
        🎬 Auto Clipper
      </h1>
      <p className="text-xl text-gray-400 mb-4">
        Transform long videos into viral short clips
      </p>
      <div className="inline-flex items-center gap-2 bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30 px-4 py-2 rounded-full">
        <span className="text-green-400 font-semibold text-sm">
          ✨ No recurring fees - 100% offline
        </span>
      </div>
    </header>
  )
}
