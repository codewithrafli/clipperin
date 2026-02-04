#!/usr/bin/env bash
# Render clips from chapters

VIDEO="${1:?Usage: $0 <video> <chapters.json> [output_dir]}"
CHAPTERS="${2:?Usage: $0 <video> <chapters.json> [output_dir]}"
OUTPUT_DIR="${3:-./output}"

clipper render "$VIDEO" "$CHAPTERS" -o "$OUTPUT_DIR" "${@:4}"
