# Architecture

## Overview

Auto Clipper is a modular, self-hosted video clipping solution designed with clear separation of concerns.

## Module Structure

```
auto-clipper/
├── clipperin-core/     # Pure Python library (no UI, no CLI)
├── clipperin-cli/      # Command-line interface
├── clipperin-ui/       # Web UI (FastAPI + React)
├── scripts/          # Shell script wrappers
└── docker/           # Container configurations
```

## Core Principles

1. **Core is library-only** - `clipperin-core` has zero dependencies on CLI/UI frameworks
2. **CLI consumes core** - `clipperin-cli` is a thin wrapper around `clipperin-core`
3. **UI is optional** - The web UI calls the same core APIs as the CLI
4. **No circular dependencies** - All dependency arrows point toward core

## Data Flow

```
User Input
    ↓
┌─────────────┐
│  CLI / UI   │
└──────┬──────┘
       │
┌──────▼──────────────────────┐
│      Pipeline Orchestration │
│  (Download → Transcribe →   │
│   Analyze → Render)         │
└──────┬──────────────────────┘
       │
┌──────▼──────────────────────┐
│      Processors             │
│  (Downloader, Transcriber,   │
│   Analyzer, Renderer)       │
└──────┬──────────────────────┘
       │
┌──────▼──────────────────────┐
│      AI Providers           │
│  (Gemini, Groq, OpenAI)     │
└─────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Core | Python 3.11+, dataclasses |
| CLI | Typer, Rich |
| UI Backend | FastAPI, Pydantic |
| UI Frontend | React, Chakra UI, Vite |
| Processing | FFmpeg, yt-dlp, Whisper |
| Queue | Redis, Celery |
| Container | Docker, Docker Compose |
