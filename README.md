# 🎬 Auto Clipper Engine

[![CI](https://github.com/codewithrafli/clipperin/actions/workflows/ci.yml/badge.svg)](https://github.com/codewithrafli/clipperin/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**Self-hosted video clipping solution. No recurring API fees - 100% offline processing!**

Transform long YouTube videos into viral short clips (9:16 vertical) automatically. Alternative to OpusClip & CapCut without monthly subscriptions.

## ✨ Features

### Core Features
- 🎥 **Video Download** - Supports YouTube and other platforms via yt-dlp
- 🎧 **AI Transcription** - Local Whisper model (no OpenAI API needed)
- 📝 **7 Caption Styles** - Professional-looking burned-in subtitles
- 📊 **Web Dashboard** - Beautiful UI to manage your clips

### AI Features (Optional)
- 🪝 **Auto Hook** - Generate viral intro text overlay (AI-powered)
- 🎯 **Smart Reframe** - Track speaker face, keep centered (FREE - uses OpenCV)
- 📐 **Dynamic Layout** - Auto switch single/split view (FREE)
- 🧠 **AI Chapter Analysis** - Smart detection of highlights in videos

### Output Options
- 📱 **Multiple Aspect Ratios** - 9:16 (TikTok/Reels), 1:1 (Square), 4:5 (IG/FB)
- 📊 **Progress Bar** - Customizable color and style
- 🌐 **Translation** - Optional subtitle translation

### Two-Phase Processing
1. **Phase 1**: Download → Transcribe → AI Analysis → Generate Chapters
2. **Phase 2**: Select chapters → Export clips with subtitles

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
4. Wait for processing:
   - Video downloads
   - Transcribes with Whisper
   - AI analyzes chapters
5. **Select chapters** you want to clip
6. Download your vertical short videos!

## ⚙️ Configuration

Edit `.env` to customize:

```bash
# Whisper Model: tiny, base, small, medium, large
# Larger = more accurate but slower
WHISPER_MODEL=base

# Whisper Language (optional - leave empty for auto-detect)
# Common: en (English), id (Indonesian), ms (Malay)
WHISPER_LANGUAGE=

# ===========================================
# AI PROVIDER SETTINGS
# ===========================================
# Choose: "gemini", "groq", "openai", or "none"
# "none" = free rule-based detection (no AI needed)
AI_PROVIDER=groq

# API Keys (only need ONE based on your provider)
GROQ_API_KEY=          # Get at: https://console.groq.com
GEMINI_API_KEY=        # Get at: https://aistudio.google.com
OPENAI_API_KEY=        # Get at: https://platform.openai.com

# ===========================================
# AI FEATURES
# ===========================================
# Auto Hook - Generate viral intro text
ENABLE_AUTO_HOOK=false
HOOK_DURATION=5

# Smart Reframe - Track speaker face (FREE)
ENABLE_SMART_REFRAME=false

# ===========================================
# OUTPUT SETTINGS
# ===========================================
# Aspect Ratio: "9:16", "1:1", "4:5"
OUTPUT_ASPECT_RATIO=9:16

# Progress Bar
ENABLE_PROGRESS_BAR=true
PROGRESS_BAR_COLOR=#FF0050

# Video Quality
OUTPUT_WIDTH=1080
OUTPUT_HEIGHT=1920
OUTPUT_CRF=23
```

## 💰 AI Provider Costs

| Provider | Cost/Video | Free Tier |
|----------|------------|-----------|
| **Gemini** | FREE | Unlimited |
| **Groq** | ~Rp 40 | $10 credit |
| **OpenAI** | ~Rp 650 | Pay-as-you-go |
| **None** | FREE | Rule-based |

> Note: Smart Reframe & Transcription are **always FREE** (uses OpenCV + Whisper)

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Submit new clipping job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{id}` | Get job status |
| `GET` | `/api/jobs/{id}/chapters` | Get generated chapters |
| `POST` | `/api/jobs/{id}/select-chapters` | Select chapters to clip |
| `GET` | `/api/jobs/{id}/download` | Download output video |
| `DELETE` | `/api/jobs/{id}` | Delete job and files |
| `GET` | `/api/caption-styles` | Get available caption styles |
| `GET` | `/api/ai-providers` | Get available AI providers |
| `GET` | `/api/ai-features` | Get AI feature status |
| `POST` | `/api/settings` | Update settings |

### Example: Submit via cURL

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=VIDEO_ID",
    "caption_style": "default",
    "use_ai_detection": true,
    "enable_auto_hook": true,
    "enable_smart_reframe": true
  }'
```

## 📁 Project Structure

```
clipper-engine/
├── packages/
│   ├── clipperin-core/     # Pure Python library (no UI/CLI)
│   │   ├── models/       # Job, Chapter, Clip, Config
│   │   ├── pipeline/     # Pipeline orchestration & stages
│   │   ├── processors/   # Downloader, Transcriber, Analyzer, Renderer
│   │   ├── ai/           # AI providers (Gemini, Groq, OpenAI)
│   │   └── utils/        # Video, audio, time utilities
│   ├── clipperin-cli/      # Command-line interface
│   │   ├── commands/     # CLI commands (download, transcribe, etc.)
│   │   ├── output/       # Table, progress, JSON formatting
│   │   └── config/       # Settings management
│   └── clipperin-ui/       # Web UI
│       ├── backend/      # FastAPI server
│       └── frontend/     # React SPA
├── scripts/              # Shell wrappers
├── docker/               # Container configs
├── docs/                 # Architecture, API, Contributing
└── data/                 # Output videos
    └── jobs/             # Job folders
```

## 🏗️ Architecture

This project uses a **modular architecture** with clear separation:

1. **clipperin-core** - Pure Python library, usable independently
2. **clipperin-cli** - Thin CLI wrapper around core
3. **clipperin-ui** - Optional web UI using same core APIs

See [docs/architecture.md](docs/architecture.md) for details.

## 🔧 CLI Usage

```bash
# Install
pip install -e "./packages/clipperin-core[full]"
pip install -e "./packages/clipperin-cli[full]"

# Full pipeline
clipperin pipeline "https://youtube.com/watch?v=xxx" -o ./output

# Step by step
clipperin download "url" -o video.mp4
clipperin transcribe video.mp4 -o subs.srt
clipperin analyze subs.srt -o chapters.json --ai groq
clipperin render video.mp4 chapters.json -o ./clips

# Config
clipperin config --list
clipperin config ai.provider groq
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

## 🙏 Support

Clipperin is free and open-source (MIT License). If you find this tool useful and want to support its development, you can donate via:

**Trakteer** (Indonesian crowdfunding)
- [trakteer.id/codewithrafli](https://trakteer.id/codewithrafli)

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for content creators.**
