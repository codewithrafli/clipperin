"""Transcription pipeline stage."""

from pathlib import Path

from clipperin_core.models.job import Job, JobStatus
from clipperin_core.pipeline.base import PipelineStage
from clipperin_core.processors.transcriber import AudioTranscriber, TranscriptionResult


class TranscribeStage(PipelineStage):
    """
    Transcribe video audio to text.

    Input: job.video_path
    Output: job.srt_path, job.transcription
    """

    name = "transcribe"

    def __init__(self, transcriber: AudioTranscriber):
        self.transcriber = transcriber

    def validate(self, job: Job) -> tuple[bool, str | None]:
        """Validate job has video file."""
        if not job.video_path or not Path(job.video_path).exists():
            return False, "Job must have a valid video_path"
        return True, None

    def pre_execute(self, job: Job) -> None:
        """Update job status."""
        job.update_status(JobStatus.TRANSCRIBING, progress=0)

    def execute(self, job: Job, **kwargs) -> TranscriptionResult:
        """
        Transcribe the video audio.

        Args:
            job: Job with video to transcribe

        Returns:
            TranscriptionResult
        """
        result = self.transcriber.transcribe(
            job.video_path,
            progress_callback=lambda p: job.update_status(JobStatus.TRANSCRIBING, progress=p),
        )

        # Save SRT
        job_dir = job.video_path.parent
        srt_path = job_dir / f"{job.id}.srt"
        self.transcriber.to_srt(result, srt_path)

        job.srt_path = srt_path
        job.transcription = result.segments
        job.update_status(JobStatus.TRANSCRIBING, progress=100)

        return result

    def post_execute(self, job: Job, result: TranscriptionResult) -> None:
        """Store transcription result."""
        job.transcription = result.segments
        job.metadata["language"] = result.language
        job.metadata["duration"] = result.duration
