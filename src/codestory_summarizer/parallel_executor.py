"""Parallel executor for processing nodes in the dependency graph.

This module provides functionality for processing nodes in parallel with
configurable concurrency limits.
"""

import asyncio
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .models import DependencyGraph, NodeData, ProcessingStatus

# Set up logging
logger = logging.getLogger(__name__)


class ParallelExecutor:
    """Manages parallel processing of nodes with configurable concurrency limits.

    This class handles the parallel execution of tasks on nodes in the
    dependency graph, respecting the DAG order and limiting concurrency.
    """

    def __init__(
        self, max_concurrency: int = 5, executor: ThreadPoolExecutor | None = None
    ):
        """Initialize the parallel executor.

        Args:
            max_concurrency: Maximum number of concurrent tasks
            executor: Optional thread pool executor to use
        """
        self.max_concurrency = max_concurrency
        self.executor = executor or ThreadPoolExecutor(max_workers=max_concurrency)
        self.active_tasks: dict[str, asyncio.Future] = {}
        self.completed_tasks: set[str] = set()
        self.failed_tasks: set[str] = set()
        self.task_queue: list[str] = []
        self.graph: DependencyGraph | None = None
        self.processing_function: Callable | None = None
        self.loop: asyncio.AbstractEventLoop | None = None

    async def process_graph(
        self,
        graph: DependencyGraph,
        process_func: Callable[[str, NodeData], Any],
        on_completion: Callable | None = None,
    ) -> DependencyGraph:
        """Process all nodes in the dependency graph.

        Args:
            graph: Dependency graph to process
            process_func: Function to call for each node, taking node_id and node_data
            on_completion: Optional callback to call when a node is completed

        Returns:
            DependencyGraph: Updated graph with processing status
        """
        self.graph = graph
        self.processing_function = process_func
        self.loop = asyncio.get_event_loop()

        logger.info(
            f"Starting parallel processing with max concurrency: {self.max_concurrency}"
        )

        # Get initial leaf nodes
        ready_nodes = self.graph.get_ready_nodes()
        self.task_queue.extend(ready_nodes)

        # Process all nodes in the graph
        while (
            self.task_queue or self.active_tasks
        ) and self.graph.completed_count < self.graph.total_count:
            # Start new tasks up to the concurrency limit
            while self.task_queue and len(self.active_tasks) < self.max_concurrency:
                await self._start_next_task()

            # Wait for any task to complete
            if self.active_tasks:
                done, _ = await asyncio.wait(
                    list(self.active_tasks.values()),
                    return_when=asyncio.FIRST_COMPLETED,
                )

                # Process completed tasks
                for task in done:
                    node_id, success = task.result()
                    await self._handle_completed_task(node_id, success, on_completion)

            # If no active tasks but queue is empty, find more ready nodes
            if not self.active_tasks and not self.task_queue:
                ready_nodes = self.graph.get_ready_nodes()
                self.task_queue.extend(ready_nodes)

                # If no more nodes are ready, there might be a cycle or all nodes are processed
                if not ready_nodes:
                    # Check if all nodes are processed
                    if (
                        self.graph.completed_count
                        + self.graph.failed_count
                        + self.graph.skipped_count
                        < self.graph.total_count
                    ):
                        logger.warning(
                            "No more nodes can be processed but not all nodes are complete. "
                            "There might be a cycle."
                        )
                        self._fail_remaining_nodes()
                    break

            # Short sleep to prevent CPU spinning
            await asyncio.sleep(0.1)

        logger.info(
            f"Processing complete. {self.graph.completed_count}/{self.graph.total_count} "
            f"nodes processed successfully."
        )
        return self.graph

    async def _start_next_task(self) -> None:
        """Start the next task from the queue."""
        if not self.task_queue:
            return

        node_id = self.task_queue.pop(0)
        if not self.graph or node_id not in self.graph.nodes:
            logger.warning(f"Node {node_id} not found in graph")
            return

        # Mark node as processing
        self.graph.update_node_status(node_id, ProcessingStatus.PROCESSING)

        # Start task
        if not self.loop:
            self.loop = asyncio.get_event_loop()

        task = self.loop.run_in_executor(
            self.executor, self._execute_task, node_id, self.graph.nodes[node_id]
        )

        self.active_tasks[node_id] = task

    def _execute_task(self, node_id: str, node_data: NodeData) -> tuple[str, bool]:
        """Execute the processing function for a node.

        Args:
            node_id: ID of the node to process
            node_data: Data for the node

        Returns:
            tuple[str, bool]: Node ID and success flag
        """
        try:
            if not self.processing_function:
                logger.error("Processing function is not set")
                return node_id, False

            self.processing_function(node_id, node_data)
            return node_id, True
        except Exception as e:
            logger.exception(f"Error processing node {node_id}: {e}")
            return node_id, False

    async def _handle_completed_task(
        self, node_id: str, success: bool, on_completion: Callable | None = None
    ) -> None:
        """Handle a completed task.

        Args:
            node_id: ID of the completed node
            success: Whether the task succeeded
            on_completion: Optional callback to call when a node is completed
        """
        # Remove from active tasks
        if node_id in self.active_tasks:
            del self.active_tasks[node_id]

        # Check if graph exists
        if not self.graph:
            logger.error("Graph is not initialized")
            return

        # Update status
        if success:
            self.graph.update_node_status(node_id, ProcessingStatus.COMPLETED)
            self.completed_tasks.add(node_id)

            # Call completion callback if provided
            if on_completion and node_id in self.graph.nodes:
                try:
                    on_completion(node_id, self.graph.nodes[node_id])
                except Exception as e:
                    logger.exception(
                        f"Error in completion callback for node {node_id}: {e}"
                    )
        else:
            self.graph.update_node_status(node_id, ProcessingStatus.FAILED)
            self.failed_tasks.add(node_id)

        # Check if any dependent nodes are now ready
        if node_id in self.graph.nodes:
            for dep_id in self.graph.nodes[node_id].dependents:
                if (
                    dep_id in self.graph.nodes
                    and self.graph.nodes[dep_id].status == ProcessingStatus.PENDING
                ):
                    # Check if all dependencies of this node are processed
                    dependencies_processed = True
                    for dep_dep_id in self.graph.nodes[dep_id].dependencies:
                        if dep_dep_id not in self.graph.nodes:
                            continue

                        dep_dep_status = self.graph.nodes[dep_dep_id].status
                        if dep_dep_status not in (
                            ProcessingStatus.COMPLETED,
                            ProcessingStatus.SKIPPED,
                        ):
                            dependencies_processed = False
                            break

                    if dependencies_processed:
                        self.graph.update_node_status(dep_id, ProcessingStatus.READY)
                        self.task_queue.append(dep_id)

    def _fail_remaining_nodes(self) -> None:
        """Mark all remaining pending nodes as failed."""
        if not self.graph:
            logger.error("Graph is not initialized")
            return

        for node_id, node in self.graph.nodes.items():
            if node.status == ProcessingStatus.PENDING:
                self.graph.update_node_status(node_id, ProcessingStatus.FAILED)
