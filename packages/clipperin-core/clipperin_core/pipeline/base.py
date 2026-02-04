"""Base pipeline and stage abstractions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar

from clipperin_core.models.job import Job, JobStatus


T = TypeVar("T")


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    success: bool
    job: Job
    stage_results: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    skipped_stages: list[str] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        """Check if the pipeline had any error."""
        return not self.success or bool(self.error)


class PipelineStage(ABC):
    """
    Abstract base class for pipeline stages.

    Each stage represents a single step in the video processing pipeline.
    """

    name: str = "base_stage"

    @abstractmethod
    def execute(self, job: Job, **kwargs) -> Any:
        """
        Execute the stage logic.

        Args:
            job: The job to process
            **kwargs: Additional stage-specific parameters

        Returns:
            Stage-specific result data
        """
        pass

    @abstractmethod
    def validate(self, job: Job) -> tuple[bool, Optional[str]]:
        """
        Validate that the job is ready for this stage.

        Args:
            job: The job to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    def pre_execute(self, job: Job) -> None:
        """Hook called before execution."""
        pass

    def post_execute(self, job: Job, result: Any) -> None:
        """Hook called after execution."""
        pass

    def on_progress(self, job: Job, progress: float, message: str = "") -> None:
        """
        Report progress for this stage.

        Args:
            job: The job being processed
            progress: Progress value (0-100)
            message: Optional progress message
        """
        # This can be overridden to emit events or call callbacks
        pass


class Pipeline:
    """
    Orchestrate multiple pipeline stages.

    Stages are executed in order. Failed stages stop execution.
    """

    def __init__(
        self,
        stages: list[PipelineStage],
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ):
        self.stages = stages
        self.progress_callback = progress_callback

    def execute(
        self,
        job: Job,
        stop_at: Optional[str] = None,
        skip_to: Optional[str] = None,
        **kwargs,
    ) -> PipelineResult:
        """
        Execute the pipeline for a job.

        Args:
            job: The job to process
            stop_at: Optional stage name to stop after
            skip_to: Optional stage name to skip to
            **kwargs: Additional parameters passed to all stages

        Returns:
            PipelineResult with execution details
        """
        result = PipelineResult(success=True, job=job)
        stage_results = {}

        # Find starting index if skip_to is specified
        start_idx = 0
        if skip_to:
            for i, stage in enumerate(self.stages):
                if stage.name == skip_to:
                    start_idx = i
                    result.skipped_stages = [s.name for s in self.stages[:i]]
                    break

        for stage in self.stages[start_idx:]:
            # Check stop condition
            if stop_at and stage.name == stop_at:
                break

            # Validate stage
            valid, error = stage.validate(job)
            if not valid:
                result.success = False
                result.error = f"Stage '{stage.name}' validation failed: {error}"
                return result

            # Execute stage
            try:
                stage.pre_execute(job)

                stage_result = stage.execute(job, **kwargs)
                stage_results[stage.name] = stage_result

                stage.post_execute(job, stage_result)

                # Report progress
                if self.progress_callback:
                    overall_progress = (list(self.stages).index(stage) + 1) / len(self.stages) * 100
                    self.progress_callback(stage.name, overall_progress, "")

            except Exception as e:
                result.success = False
                result.error = f"Stage '{stage.name}' failed: {str(e)}"
                job.update_status(JobStatus.FAILED, error=str(e))
                return result

        result.stage_results = stage_results
        return result

    def add_stage(self, stage: PipelineStage, position: Optional[int] = None) -> None:
        """
        Add a stage to the pipeline.

        Args:
            stage: Stage to add
            position: Optional position to insert at (default: append)
        """
        if position is not None:
            self.stages.insert(position, stage)
        else:
            self.stages.append(stage)

    def remove_stage(self, stage_name: str) -> bool:
        """
        Remove a stage from the pipeline.

        Args:
            stage_name: Name of stage to remove

        Returns:
            True if stage was removed
        """
        self.stages = [s for s in self.stages if s.name != stage_name]
        return True

    def get_stage(self, stage_name: str) -> Optional[PipelineStage]:
        """Get a stage by name."""
        for stage in self.stages:
            if stage.name == stage_name:
                return stage
        return None


class FullPipeline(Pipeline):
    """
    Complete video clipping pipeline.

    Runs all stages: download -> transcribe -> analyze -> render
    """

    def __init__(
        self,
        downloader,
        transcriber,
        analyzer,
        renderer,
        progress_callback: Optional[Callable[[str, float, str], None]] = None,
    ):
        from clipperin_core.pipeline.stages.download import DownloadStage
        from clipperin_core.pipeline.stages.transcribe import TranscribeStage
        from clipperin_core.pipeline.stages.analyze import AnalyzeStage
        from clipperin_core.pipeline.stages.render import RenderStage

        stages = [
            DownloadStage(downloader),
            TranscribeStage(transcriber),
            AnalyzeStage(analyzer),
            RenderStage(renderer),
        ]

        super().__init__(stages, progress_callback)
