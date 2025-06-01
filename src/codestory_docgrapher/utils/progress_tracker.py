r"""Progress tracker for documentation processing.

This module provides functionality for tracking the progress of
documentation processing during the DocumentationGrapher step.
"""
import logging
import time

from ..models import DocumentationGraph

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks progress of documentation processing.

    This class provides methods for tracking and reporting the progress
    of documentation processing during the DocumentationGrapher step.
    """

    def __init__(self, graph: DocumentationGraph) -> None:
        """Initialize the progress tracker.

        Args:
            graph: Documentation graph to track progress for
        """
        self.graph = graph
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 5.0
        self.total_documents = 0
        self.processed_documents = 0
        self.total_entities = 0
        self.processed_entities = 0

    def set_total_documents(self, count: int) -> None:
        """Set the total number of documents to process.

        Args:
            count: Total number of documents
        """
        self.total_documents = count
        self.graph.total_files = count

    def document_processed(self) -> None:
        """Mark a document as processed.

        This increments the processed document count and updates progress.
        """
        self.processed_documents += 1
        self.graph.processed_files += 1

    def entity_processed(self) -> None:
        """Mark an entity as processed.

        This increments the processed entity count.
        """
        self.processed_entities += 1

    def get_progress(self) -> float:
        """Get the overall progress as a percentage.

        Returns:
            Progress percentage (0-100)
        """
        if self.total_documents == 0:
            return 0.0
        return min(self.processed_documents / self.total_documents * 100.0, 100.0)

    def get_elapsed_time(self) -> float:
        """Get the elapsed time in seconds.

        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time

    def get_estimated_remaining_time(self) -> float | None:
        """Get the estimated remaining time in seconds.

        Returns:
            Estimated remaining time in seconds, or None if unknown
        """
        progress = self.get_progress()
        if progress <= 0:
            return None
        elapsed = self.get_elapsed_time()
        total_estimated = elapsed / (progress / 100.0)
        remaining = total_estimated - elapsed
        return max(0, remaining)

    def should_update(self) -> bool:
        """Check if progress should be updated.

        Returns:
            True if progress should be updated, False otherwise
        """
        now = time.time()
        if now - self.last_update_time >= self.update_interval:
            self.last_update_time = now
            return True
        return False

    def update_progress(self) -> str:
        """Update and log progress.

        Returns:
            Progress message
        """
        progress = self.get_progress()
        elapsed = self.get_elapsed_time()
        remaining = self.get_estimated_remaining_time()
        message = f"Progress: {progress:.1f}% ({self.processed_documents}/{self.total_documents} files) | Elapsed: {self._format_time(elapsed)}"
        if remaining is not None:
            message += f" | Remaining: {self._format_time(remaining)}"
        message += f" | Entities: {self.processed_entities}, Relationships: {len(self.graph.relationships)}"
        logger.info(message)
        return message

    def _format_time(self, seconds: float) -> str:
        """Format a time duration in a human-readable way.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            minutes = seconds % 3600 / 60
            return f"{hours:.1f}h {minutes:.0f}m"

    def get_status_dict(self) -> dict[str, float | int]:
        """Get the current status as a dictionary.

        Returns:
            Dict with status information
        """
        progress = self.get_progress()
        elapsed = self.get_elapsed_time()
        remaining = self.get_estimated_remaining_time()
        status = {
            "progress": progress,
            "elapsed_time": elapsed,
            "processed_documents": self.processed_documents,
            "total_documents": self.total_documents,
            "processed_entities": self.processed_entities,
            "relationships": len(self.graph.relationships),
        }
        if remaining is not None:
            status["remaining_time"] = remaining
        return status
