#!/usr/bin/env bash
set -e

URL="$1"

if [ -z "$URL" ]; then
  echo "Usage: ./auto_clip.sh <youtube_url>"
  exit 1
fi

echo "⬇️ Downloading video..."
yt-dlp \
-f "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]" \
--merge-output-format mp4 \
-o "input.mp4" \
"$URL"

echo "🎧 Generating subtitles..."
whisper input.mp4 --model base --output_format srt --output_dir .

echo "✂️ Creating Shorts clip..."
ffmpeg -ss 00:00:30 -t 00:00:30 -i input.mp4 \
-vf "
crop=ih*9/16:ih:(iw-ih*9/16)/2:0,
scale=1080:1920,
drawtext=text='KESALAHAN BESAR DI BISNIS KELUARGA':
fontcolor=white:fontsize=64:x=(w-text_w)/2:y=120:
box=1:boxcolor=black@0.65:enable='between(t,0,3)',
subtitles=input.srt:force_style='FontName=Arial Black,FontSize=48,Outline=3,Alignment=2',
eq=contrast=1.05:saturation=1.1,
zoompan=z='min(zoom+0.0005,1.05)':d=1:s=1080x1920
" \
-c:v libx264 -preset veryfast -crf 23 \
-c:a aac \
output.mp4

echo "🎉 DONE! output.mp4 ready"
