from typing import Any

"Data models for summaries and intermediate representations.\n\nThis module defines the data models used by the Summarizer workflow step\nfor representing summaries and tracking processing state.\n"
from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes that can be summarized."""

    REPOSITORY = "Repository"
    DIRECTORY = "Directory"
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    METHOD = "Method"
    MODULE = "Module"
    VARIABLE = "Variable"
    NAMESPACE = "Namespace"


class ProcessingStatus(str, Enum):
    """Status of a node in the summarization process."""

    PENDING = "pending"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class NodeData(BaseModel):
    """Data for a node in the dependency graph."""

    id: str
    name: str
    type: NodeType
    path: str | None = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    dependencies: set[str] = Field(default_factory=set)
    dependents: set[str] = Field(default_factory=set)
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)


class SummaryData(BaseModel):
    """Data for a generated summary."""

    node_id: str
    node_type: NodeType
    summary: str
    code_snippets: list[str] = Field(default_factory=list)
    token_count: int = 0
    confidence: float = 1.0
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DependencyGraph(BaseModel):
    """Represents the dependency graph of nodes to be summarized."""

    nodes: dict[str, NodeData] = Field(default_factory=dict)
    leaf_nodes: set[str] = Field(default_factory=set)
    root_nodes: set[str] = Field(default_factory=set)
    pending_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_count: int = 0

    def add_node(self, node: NodeData) -> None:
        """Add a node to the graph.

        Args:
            node: Node data to add
        """
        self.nodes[node.id] = node
        self.pending_count += 1
        self.total_count += 1
        if not node.dependencies:
            self.leaf_nodes.add(node.id)
        if not node.dependents:
            self.root_nodes.add(node.id)

    def update_node_status(self, node_id: str, status: ProcessingStatus) -> None:
        """Update the status of a node.

        Args:
            node_id: ID of the node to update
            status: New status
        """
        if node_id not in self.nodes:
            return
        old_status = self.nodes[node_id].status
        self.nodes[node_id].status = status
        if old_status == ProcessingStatus.PENDING:
            self.pending_count -= 1
        elif old_status == ProcessingStatus.PROCESSING:
            self.processing_count -= 1
        elif old_status == ProcessingStatus.COMPLETED:
            self.completed_count -= 1
        elif old_status == ProcessingStatus.FAILED:
            self.failed_count -= 1
        elif old_status == ProcessingStatus.SKIPPED:
            self.skipped_count -= 1
        if status == ProcessingStatus.PENDING:
            self.pending_count += 1
        elif status == ProcessingStatus.PROCESSING:
            self.processing_count += 1
        elif status == ProcessingStatus.COMPLETED:
            self.completed_count += 1
        elif status == ProcessingStatus.FAILED:
            self.failed_count += 1
        elif status == ProcessingStatus.SKIPPED:
            self.skipped_count += 1

    def get_ready_nodes(self) -> list[str]:
        """Get nodes that are ready to be processed.

        A node is ready when all its dependencies have been processed.

        Returns:
            List of node IDs that are ready to be processed
        """
        ready_nodes = []
        for node_id, node in self.nodes.items():
            if node.status != ProcessingStatus.PENDING:
                continue
            dependencies_processed = True
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    continue
                dep_status = self.nodes[dep_id].status
                if dep_status not in (
                    ProcessingStatus.COMPLETED,
                    ProcessingStatus.SKIPPED,
                ):
                    dependencies_processed = False
                    break
            if dependencies_processed:
                ready_nodes.append(node_id)
                self.update_node_status(node_id, ProcessingStatus.READY)
        return ready_nodes

    def get_progress(self) -> float:
        """Get the overall progress as a percentage.

        Returns:
            Progress percentage (0-100)
        """
        if self.total_count == 0:
            return 100.0
        processed = self.completed_count + self.failed_count + self.skipped_count
        return processed / self.total_count * 100.0
