"""Download pipeline stage."""

from pathlib import Path

from clipper_core.models.job import Job, JobStatus
from clipper_core.pipeline.base import PipelineStage
from clipper_core.processors.downloader import VideoDownloader


class DownloadStage(PipelineStage):
    """
    Download video from URL.

    Input: job.url
    Output: job.video_path
    """

    name = "download"

    def __init__(self, downloader: VideoDownloader):
        self.downloader = downloader

    def validate(self, job: Job) -> tuple[bool, str | None]:
        """Validate job has required URL."""
        if not job.url:
            return False, "Job must have a URL"
        return True, None

    def pre_execute(self, job: Job) -> None:
        """Update job status."""
        job.update_status(JobStatus.DOWNLOADING, progress=0)

    def execute(self, job: Job, output_dir: Path | None = None, **kwargs) -> Path:
        """
        Download the video.

        Args:
            job: Job with URL to download
            output_dir: Optional custom output directory

        Returns:
            Path to downloaded video
        """
        output_path = output_dir or job.output_dir

        video_path = self.downloader.download(
            job.url,
            output_path=output_path / f"{job.id}.mp4" if output_path else None,
            progress_callback=lambda p: job.update_status(JobStatus.DOWNLOADING, progress=p),
        )

        job.video_path = video_path
        job.update_status(JobStatus.DOWNLOADING, progress=100)
        return video_path

    def post_execute(self, job: Job, result: Path) -> None:
        """Update job with video path."""
        job.video_path = result
        job.metadata["downloaded_at"] = result.stat().st_mtime if result.exists() else None
