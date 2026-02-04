#!/usr/bin/env bash
# Transcribe video to subtitles

VIDEO="${1:?Usage: $0 <video> [output]}"
OUTPUT="${2:-subtitles.srt}"

clipper transcribe "$VIDEO" -o "$OUTPUT"
