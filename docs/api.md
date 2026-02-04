# API Reference

## Core Library API

### Models

```python
from clipperin_core import Job, Chapter, Clip, Config

# Create a job
job = Job(url="https://youtube.com/watch?v=xxx")

# Create configuration
config = Config()
config.whisper.model = WhisperModel.BASE
config.ai.provider = AIProviderType.GROQ
```

### Pipeline

```python
from clipperin_core import Pipeline, FullPipeline
from clipperin_core import VideoDownloader, AudioTranscriber, ContentAnalyzer, VideoRenderer

# Create processors
downloader = VideoDownloader()
transcriber = AudioTranscriber()
analyzer = ContentAnalyzer()
renderer = VideoRenderer()

# Run full pipeline
pipeline = FullPipeline(downloader, transcriber, analyzer, renderer)
result = pipeline.execute(job)
```

### Individual Stages

```python
from clipperin_core.pipeline.stages import DownloadStage, TranscribeStage

stage = DownloadStage(downloader)
stage.validate(job)  # Check if ready
stage.execute(job)   # Run the stage
```

## CLI API

### Commands

```bash
# Download video
clipperin download "https://youtube.com/watch?v=xxx" -o video.mp4

# Transcribe
clipperin transcribe video.mp4 -o subtitles.srt

# Analyze
clipperin analyze subtitles.srt -o chapters.json --ai groq

# Render
clipperin render video.mp4 chapters.json -o ./clips

# Full pipeline
clipperin pipeline "https://youtube.com/watch?v=xxx" -o ./output
```

## REST API

### Jobs

```bash
# Create job
POST /api/jobs
{
  "url": "https://youtube.com/watch?v=xxx",
  "caption_style": "default",
  "use_ai_detection": true
}

# List jobs
GET /api/jobs

# Get job status
GET /api/jobs/{job_id}

# Delete job
DELETE /api/jobs/{job_id}

# Get chapters
GET /api/jobs/{job_id}/chapters

# Select chapters for rendering
POST /api/jobs/{job_id}/select-chapters
{
  "chapter_ids": ["id1", "id2"],
  "options": {"enable_progress_bar": true}
}

# Download clip
GET /api/jobs/{job_id}/download?filename=clip.mp4
```

### Settings

```bash
# Get AI providers
GET /api/ai-providers

# Update settings
POST /api/settings
{
  "ai_provider": "groq",
  "groq_api_key": "sk-xxx"
}
```
