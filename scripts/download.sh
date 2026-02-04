#!/usr/bin/env bash
# Download video from URL

URL="${1:?Usage: $0 <url> [output]}"
OUTPUT="${2:-video.mp4}"

clipperin download "$URL" -o "$OUTPUT"
