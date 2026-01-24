# 🎬 Auto Clipper Engine

**Self-hosted video clipping solution. No recurring API fees - 100% offline processing!**

Transform long YouTube videos into viral short clips automatically.

## ✨ Features

- 🎥 **Video Download** - Supports YouTube and other platforms via yt-dlp
- 🎧 **AI Transcription** - Local Whisper model (no OpenAI API needed)
- ✂️ **Auto Clipping** - Creates 9:16 vertical shorts with subtitles
- 🎨 **Styled Subtitles** - Professional-looking burned-in captions
- 📊 **Web Dashboard** - Simple UI to manage your clips

## 🚀 Quick Start

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/) installed
- At least 4GB RAM (for Whisper model)

### Installation

```bash
# 1. Clone or download this project
cd clipper-engine

# 2. Copy environment config
cp .env.example .env

# 3. Start all services
docker-compose up --build

# 4. Open http://localhost:3000
```

That's it! 🎉

## 📖 Usage

1. Open **http://localhost:3000** in your browser
2. Paste a YouTube URL
3. Click "Create Clip"
4. Wait for processing (download → transcribe → clip)
5. Download your vertical short video!

## ⚙️ Configuration

Edit `.env` to customize:

```bash
# Whisper model: tiny, base, small, medium, large
# Larger = more accurate but slower
WHISPER_MODEL=base

# Clip settings
CLIP_START=30       # Start time in seconds
CLIP_DURATION=30    # Clip length in seconds

# Output quality
OUTPUT_CRF=23       # Lower = better quality, larger file
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Submit new clipping job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{id}` | Get job status |
| `GET` | `/api/jobs/{id}/download` | Download output video |
| `DELETE` | `/api/jobs/{id}` | Delete job and files |

### Example: Submit via cURL

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=VIDEO_ID"}'
```

## 📁 Project Structure

```
clipper-engine/
├── docker-compose.yml    # Main orchestration
├── .env.example          # Configuration template
├── api/                  # FastAPI backend
│   ├── main.py           # API endpoints
│   ├── tasks.py          # Video processing (Celery)
│   └── config.py         # Settings
├── web/                  # React dashboard
│   └── src/App.jsx       # Main UI
└── data/                 # Output videos
    └── jobs/             # Job folders
```

## 🛠️ Troubleshooting

### Container won't start?
```bash
docker-compose logs api
docker-compose logs worker
```

### Out of memory?
Use a smaller Whisper model in `.env`:
```bash
WHISPER_MODEL=tiny
```

### Video download fails?
Update yt-dlp:
```bash
docker-compose exec worker pip install -U yt-dlp
```

## 📄 License

One-time purchase. Use forever. No subscriptions.

---

**Built with ❤️ for content creators who want to keep their money.**
