"""Render pipeline stage."""

from pathlib import Path
from typing import List
import uuid

from clipper_core.models.job import Job, JobStatus, Clip
from clipper_core.models.config import AspectRatio
from clipper_core.pipeline.base import PipelineStage
from clipper_core.processors.renderer import VideoRenderer, RenderResult
from clipper_core.processors.caption import CaptionRenderer


class RenderStage(PipelineStage):
    """
    Render selected chapters into video clips.

    Input: job.video_path, job.srt_path, selected chapters
    Output: job.clips
    """

    name = "render"

    def __init__(self, renderer: VideoRenderer, caption_renderer: CaptionRenderer | None = None):
        self.renderer = renderer
        self.caption_renderer = caption_renderer or CaptionRenderer()

    def validate(self, job: Job) -> tuple[bool, str | None]:
        """Validate job has required files."""
        if not job.video_path or not Path(job.video_path).exists():
            return False, "Job must have a valid video_path"
        return True, None

    def pre_execute(self, job: Job) -> None:
        """Update job status."""
        job.update_status(JobStatus.PROCESSING, progress=0)

    def execute(
        self,
        job: Job,
        chapter_ids: List[str] | None = None,
        caption_style_id: str = "default",
        aspect_ratio: AspectRatio = AspectRatio.PORTRAIT,
        **kwargs,
    ) -> List[Clip]:
        """
        Render selected chapters as clips.

        Args:
            job: Job to render clips from
            chapter_ids: List of chapter IDs to render (None = all)
            caption_style_id: Caption style to use
            aspect_ratio: Output aspect ratio

        Returns:
            List of rendered Clip objects
        """
        from clipper_core.models.config import CaptionStyle

        # Filter chapters to render
        chapters_to_render = job.chapters
        if chapter_ids:
            chapters_to_render = [c for c in job.chapters if c.id in chapter_ids]

        if not chapters_to_render:
            return []

        # Get caption style
        caption_style = None
        for style in CaptionStyle.get_default_styles():
            if style.id == caption_style_id:
                caption_style = style
                break

        clips = []
        job_dir = job.video_path.parent

        for i, chapter in enumerate(chapters_to_render):
            progress = (i / len(chapters_to_render)) * 100
            job.update_status(JobStatus.PROCESSING, progress=progress)

            # Generate output filename
            clip_filename = f"clip_{chapter.id[:8]}.mp4"
            output_path = job_dir / clip_filename

            # Render clip
            result = self._render_clip(
                job.video_path,
                output_path,
                chapter,
                caption_style,
                job.srt_path,
                job.enable_auto_hook,
                job.enable_smart_reframe,
                kwargs.get("enable_progress_bar", True),
                kwargs.get("progress_bar_color", "#FF0050"),
                aspect_ratio,
            )

            if result.success:
                # Generate thumbnail
                thumb_path = job_dir / f"thumb_{chapter.id[:8]}.jpg"
                self.renderer.generate_thumbnail(
                    output_path,
                    thumb_path,
                    timestamp=chapter.duration / 2,
                )

                # Create clip object
                clip = Clip.from_chapter(
                    chapter,
                    clip_filename,
                    score=chapter.metadata.get("viral_score", 75),
                )
                clip.thumbnail = thumb_path.name if thumb_path.exists() else None
                clip.srt_path = job.srt_path

                clips.append(clip)
                job.add_clip(clip)

        job.update_status(JobStatus.COMPLETED, progress=100)
        return clips

    def _render_clip(
        self,
        input_path: Path,
        output_path: Path,
        chapter,
        caption_style,
        srt_path: Path | None,
        enable_hook: bool,
        enable_smart_reframe: bool,
        enable_progress_bar: bool,
        progress_bar_color: str,
        aspect_ratio: AspectRatio,
    ) -> RenderResult:
        """Render a single clip."""
        hook_text = ""
        if enable_hook and chapter.hooks:
            hook_text = chapter.hooks[0]

        return self.renderer.render_clip(
            input_path=input_path,
            output_path=output_path,
            start=chapter.start,
            end=chapter.end,
            caption_style=caption_style,
            srt_path=srt_path,
            enable_hook=enable_hook,
            hook_text=hook_text,
            enable_smart_reframe=enable_smart_reframe,
            enable_progress_bar=enable_progress_bar,
            progress_bar_color=progress_bar_color,
            aspect_ratio=aspect_ratio,
        )

    def post_execute(self, job: Job, result: List[Clip]) -> None:
        """Store rendered clips."""
        job.clips = result
        job.metadata["clip_count"] = len(result)
