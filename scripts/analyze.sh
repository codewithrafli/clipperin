#!/usr/bin/env bash
# Analyze transcription for chapters

INPUT="${1:?Usage: $0 <transcription.srt> [output.json]}"
OUTPUT="${2:-chapters.json}"

clipperin analyze "$INPUT" -o "$OUTPUT" "${@:3}"
