# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- PyPI package publishing
- More caption styles
- Batch processing support

## [0.1.0] - 2026-02-04

### Added
- Initial release of Clipperin - Auto Clipper Engine
- Modular architecture with three packages:
  - `clipperin-core` - Core library
  - `clipperin-cli` - Command-line interface
  - `clipperin-ui` - Web dashboard (optional)
- Video download from YouTube and other platforms (yt-dlp)
- Local audio transcription using Whisper (no API fees)
- AI-powered chapter analysis (Gemini, Groq, OpenAI)
- Rule-based fallback detection (free, no AI needed)
- 7 built-in caption styles (default, karaoke, minimal, bold, neon, tiktok, typewriter)
- Multiple aspect ratios: 9:16, 1:1, 4:5
- Smart reframe with face tracking (OpenCV, free)
- Auto hook generation for viral intros
- Progress bar overlay customization
- Web UI with FastAPI backend and React frontend
- CLI commands: download, transcribe, analyze, chapters, render, config, pipeline
- Docker support for easy deployment
- MIT License

### Documentation
- README with quick start guide
- Architecture documentation
- API reference
- Contributing guidelines
- Security policy

[Unreleased]: https://github.com/codewithrafli/clipperin/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/codewithrafli/clipperin/releases/tag/v0.1.0
