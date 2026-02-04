"""Analysis pipeline stage."""

from clipper_core.models.job import Job, JobStatus
from clipper_core.pipeline.base import PipelineStage
from clipper_core.processors.analyzer import ContentAnalyzer


class AnalyzeStage(PipelineStage):
    """
    Analyze transcription to extract chapters.

    Input: job.transcription
    Output: job.chapters
    """

    name = "analyze"

    def __init__(self, analyzer: ContentAnalyzer):
        self.analyzer = analyzer

    def validate(self, job: Job) -> tuple[bool, str | None]:
        """Validate job has transcription."""
        if not job.transcription:
            return False, "Job must have transcription data"
        return True, None

    def pre_execute(self, job: Job) -> None:
        """Update job status."""
        job.update_status(JobStatus.ANALYZING, progress=0)

    def execute(self, job: Job, use_ai: bool = True, **kwargs) -> list:
        """
        Analyze transcription for chapters.

        Args:
            job: Job with transcription to analyze
            use_ai: Whether to use AI analysis

        Returns:
            List of Chapter objects
        """
        # Build transcription text
        transcription_text = " ".join([
            seg.get("text", "") for seg in job.transcription
        ])

        duration = job.metadata.get("duration", 0)

        chapters = self.analyzer.analyze_chapters(
            transcription_text,
            duration,
            use_ai=use_ai and job.use_ai,
        )

        # Score viral potential
        for chapter in chapters:
            score = self.analyzer.score_viral_potential(chapter, transcription_text)
            chapter.metadata = {"viral_score": score}

        job.chapters = chapters
        job.update_status(JobStatus.CHAPTERS_READY, progress=100)

        return chapters

    def post_execute(self, job: Job, result: list) -> None:
        """Store chapters and update status."""
        job.chapters = result
        job.metadata["chapter_count"] = len(result)
