"""Data models for summaries and intermediate representations.

This module defines the data models used by the Summarizer workflow step
for representing summaries and tracking processing state.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Union
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
    
    PENDING = "pending"      # Not yet processed
    READY = "ready"          # Ready to be processed (dependencies are processed)
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"   # Successfully processed
    FAILED = "failed"        # Processing failed
    SKIPPED = "skipped"      # Skipped (e.g., binary file)


class NodeData(BaseModel):
    """Data for a node in the dependency graph."""
    
    id: str
    name: str
    type: NodeType
    path: Optional[str] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    dependencies: Set[str] = Field(default_factory=set)
    dependents: Set[str] = Field(default_factory=set)
    properties: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)
    

class SummaryData(BaseModel):
    """Data for a generated summary."""
    
    node_id: str
    node_type: NodeType
    summary: str
    code_snippets: List[str] = Field(default_factory=list)
    token_count: int = 0
    confidence: float = 1.0
    metadata: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class DependencyGraph(BaseModel):
    """Represents the dependency graph of nodes to be summarized."""
    
    nodes: Dict[str, NodeData] = Field(default_factory=dict)
    leaf_nodes: Set[str] = Field(default_factory=set)
    root_nodes: Set[str] = Field(default_factory=set)
    
    # Keep track of progress
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
        
        # Update leaf nodes and root nodes
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
        
        # Update counts
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
    
    def get_ready_nodes(self) -> List[str]:
        """Get nodes that are ready to be processed.
        
        A node is ready when all its dependencies have been processed.
        
        Returns:
            List of node IDs that are ready to be processed
        """
        ready_nodes = []
        
        for node_id, node in self.nodes.items():
            if node.status != ProcessingStatus.PENDING:
                continue
                
            # Check if all dependencies are processed
            dependencies_processed = True
            for dep_id in node.dependencies:
                if dep_id not in self.nodes:
                    # If dependency doesn't exist, assume it's processed
                    continue
                    
                dep_status = self.nodes[dep_id].status
                if dep_status not in (ProcessingStatus.COMPLETED, ProcessingStatus.SKIPPED):
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
        return (processed / self.total_count) * 100.0