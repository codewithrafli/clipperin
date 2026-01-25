import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.tasks import generate_clip_with_subtitles, CAPTION_STYLES

# ===== PATH =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INPUT_VIDEO = os.path.join(BASE_DIR, "input.mp4")
INPUT_SRT   = os.path.join(BASE_DIR, "input.srt")
OUTPUT_MP4  = os.path.join(BASE_DIR, "test_output.mp4")

# ===== PARAM =====
START = 30        # detik mulai
DURATION = 40     # durasi clip
STYLE = CAPTION_STYLES["capcut"]  # ganti style sesuka lo

# ===== RUN =====
print("▶️ Testing local clip render...")

generate_clip_with_subtitles(
    input_file=INPUT_VIDEO,
    output_file=OUTPUT_MP4,
    srt_file=INPUT_SRT,
    start=START,
    duration=DURATION,
    style=STYLE
)

print("✅ DONE:", OUTPUT_MP4)
