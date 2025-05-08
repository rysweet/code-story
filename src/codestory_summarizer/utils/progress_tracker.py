"""Utilities for tracking and reporting summarization progress.

This module provides functionality for tracking the progress of the
summarization process and generating progress reports.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from ..models import DependencyGraph, NodeType, ProcessingStatus

# Set up logging
logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and reports summarization progress.
    
    This class provides methods for tracking the progress of the
    summarization process and generating progress reports.
    """
    
    def __init__(self, graph: DependencyGraph):
        """Initialize the progress tracker.
        
        Args:
            graph: Dependency graph to track progress for
        """
        self.graph = graph
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.update_interval = 5.0  # seconds
        self.node_type_counts: Dict[NodeType, int] = {
            node_type: 0 for node_type in NodeType
        }
        self._count_node_types()
    
    def _count_node_types(self) -> None:
        """Count the number of nodes of each type in the graph."""
        for node_data in self.graph.nodes.values():
            self.node_type_counts[node_data.type] = self.node_type_counts.get(node_data.type, 0) + 1
    
    def get_progress_stats(self) -> Dict[str, int]:
        """Get progress statistics.
        
        Returns:
            Dict with progress statistics
        """
        stats = {
            "total": self.graph.total_count,
            "completed": self.graph.completed_count,
            "processing": self.graph.processing_count,
            "pending": self.graph.pending_count,
            "failed": self.graph.failed_count,
            "skipped": self.graph.skipped_count,
        }
        
        # Add node type counts
        for node_type in NodeType:
            stats[f"{node_type.value.lower()}_count"] = self.node_type_counts[node_type]
        
        return stats
    
    def get_progress(self) -> float:
        """Get the overall progress as a percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        return self.graph.get_progress()
    
    def get_elapsed_time(self) -> float:
        """Get the elapsed time in seconds.
        
        Returns:
            Elapsed time in seconds
        """
        return time.time() - self.start_time
    
    def get_estimated_remaining_time(self) -> Optional[float]:
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
        
        message = (
            f"Progress: {progress:.1f}% ({self.graph.completed_count}/{self.graph.total_count} nodes) | "
            f"Elapsed: {_format_time(elapsed)}"
        )
        
        if remaining is not None:
            message += f" | Remaining: {_format_time(remaining)}"
        
        message += (
            f" | Completed: {self.graph.completed_count}, "
            f"Processing: {self.graph.processing_count}, "
            f"Pending: {self.graph.pending_count}, "
            f"Failed: {self.graph.failed_count}, "
            f"Skipped: {self.graph.skipped_count}"
        )
        
        logger.info(message)
        return message


def _format_time(seconds: float) -> str:
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
        minutes = (seconds % 3600) / 60
        return f"{hours:.1f}h {minutes:.0f}m"


def get_progress_message(graph: DependencyGraph) -> str:
    """Generate a progress message for a dependency graph.
    
    Args:
        graph: Dependency graph
        
    Returns:
        Progress message
    """
    progress = graph.get_progress()
    message = (
        f"Progress: {progress:.1f}% ({graph.completed_count}/{graph.total_count} nodes) | "
        f"Completed: {graph.completed_count}, "
        f"Processing: {graph.processing_count}, "
        f"Pending: {graph.pending_count}, "
        f"Failed: {graph.failed_count}, "
        f"Skipped: {graph.skipped_count}"
    )
    
    return message