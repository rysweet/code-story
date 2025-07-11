# Code Story: Implementation Plan for Simplified Architecture

This document outlines a practical implementation plan to transition from the current containerized, microservices architecture to a simplified, modular architecture optimized for local development. The plan is designed to ensure that functionality is maintained throughout the transition process, with clear milestones and validation steps.

## Phased Implementation Approach

The transition will be implemented in phases to ensure functionality is maintained throughout the process. Each phase has specific goals, tasks, and validation criteria.

### Phase 1: Storage Abstraction Layer

**Goal**: Create a storage abstraction that can work with both SQLite and Neo4j, allowing for a gradual transition while maintaining existing functionality.

#### Tasks:

1. **Define Storage Interface**:
   
   Create a comprehensive interface that captures all required functionality for graph operations.
   
   ```python
   from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union
   from datetime import datetime
   
   T = TypeVar('T')
   
   class Transaction(Protocol):
       """Protocol for transaction objects."""
       def commit(self) -> None: ...
       def rollback(self) -> None: ...
       def __enter__(self) -> 'Transaction': ...
       def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
   
   class GraphStorage(Protocol):
       """Protocol for graph storage backends."""
       
       def connect(self) -> None:
           """Establish connection to the storage backend."""
           
       def disconnect(self) -> None:
           """Close connection to the storage backend."""
           
       def is_connected(self) -> bool:
           """Check if connected to the storage backend."""
           
       def create_node(self, label: str, properties: Dict[str, Any]) -> str:
           """Create a new node with the given label and properties.
           
           Args:
               label: Node type label
               properties: Node properties as dictionary
               
           Returns:
               Unique identifier for the created node
           """
           
       def update_node(self, node_id: str, properties: Dict[str, Any]) -> None:
           """Update properties of an existing node.
           
           Args:
               node_id: Node identifier
               properties: New or updated properties
           """
           
       def delete_node(self, node_id: str) -> None:
           """Delete a node by its ID.
           
           Args:
               node_id: Node identifier
           """
           
       def create_relationship(self, start_id: str, end_id: str, type_name: str, 
                              properties: Optional[Dict[str, Any]] = None) -> str:
           """Create a relationship between two nodes.
           
           Args:
               start_id: Source node ID
               end_id: Target node ID
               type_name: Relationship type
               properties: Optional relationship properties
               
           Returns:
               Unique identifier for the created relationship
           """
           
       def update_relationship(self, relationship_id: str, properties: Dict[str, Any]) -> None:
           """Update properties of an existing relationship.
           
           Args:
               relationship_id: Relationship identifier
               properties: New or updated properties
           """
           
       def delete_relationship(self, relationship_id: str) -> None:
           """Delete a relationship by its ID.
           
           Args:
               relationship_id: Relationship identifier
           """
           
       def get_node(self, node_id: str) -> Dict[str, Any]:
           """Retrieve a node by its ID.
           
           Args:
               node_id: Node identifier
               
           Returns:
               Node data as dictionary with properties
           """
           
       def get_relationship(self, relationship_id: str) -> Dict[str, Any]:
           """Retrieve a relationship by its ID.
           
           Args:
               relationship_id: Relationship identifier
               
           Returns:
               Relationship data as dictionary with properties
           """
           
       def query(self, query_string: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
           """Execute a query against the graph.
           
           Args:
               query_string: Query in Cypher-like syntax
               params: Query parameters
               
           Returns:
               List of result records as dictionaries
           """
           
       def begin_transaction(self) -> Transaction:
           """Begin a new transaction for atomic operations.
           
           Returns:
               Transaction object with context manager support
           """
           
       def execute_in_transaction(self, func: Callable[..., T], *args, **kwargs) -> T:
           """Execute a function within a transaction.
           
           Args:
               func: Function to execute
               args, kwargs: Arguments to pass to the function
               
           Returns:
               Result of the function execution
           """
           
       def get_nodes_by_label(self, label: str, properties: Optional[Dict[str, Any]] = None, 
                             limit: int = 100) -> List[Dict[str, Any]]:
           """Find nodes by label and optional property filters.
           
           Args:
               label: Node type label
               properties: Optional property filters
               limit: Maximum number of results
               
           Returns:
               List of matching nodes
           """
           
       def get_relationships(self, node_id: str, relationship_type: Optional[str] = None, 
                           direction: str = "OUTGOING") -> List[Dict[str, Any]]:
           """Get relationships for a node.
           
           Args:
               node_id: Node identifier
               relationship_type: Optional relationship type filter
               direction: Relationship direction ("OUTGOING", "INCOMING", "BOTH")
               
           Returns:
               List of relationships with connected nodes
           """
           
       def count_nodes(self, label: Optional[str] = None) -> int:
           """Count nodes with optional label filter.
           
           Args:
               label: Optional node label filter
               
           Returns:
               Number of matching nodes
           """
           
       def count_relationships(self, type_name: Optional[str] = None) -> int:
           """Count relationships with optional type filter.
           
           Args:
               type_name: Optional relationship type filter
               
           Returns:
               Number of matching relationships
           """
           
       def clear(self) -> None:
           """Clear all data from the storage."""
   ```

2. **Implement Neo4j Adapter**:
   
   Wrap the existing Neo4j connector with the new interface, ensuring proper resource management and optimization.
   
   ```python
   import neo4j
   from neo4j import GraphDatabase
   from typing import Any, Dict, List, Optional, Callable, TypeVar
   
   T = TypeVar('T')
   
   class Neo4jTransaction:
       """Neo4j transaction wrapper."""
       
       def __init__(self, tx):
           self._tx = tx
           
       def commit(self) -> None:
           """Commit the transaction."""
           # Neo4j driver handles commit automatically at context exit
           pass
           
       def rollback(self) -> None:
           """Rollback the transaction."""
           # Neo4j Python driver doesn't expose explicit rollback,
           # but it will rollback on exception
           pass
           
       def __enter__(self) -> 'Neo4jTransaction':
           return self
           
       def __exit__(self, exc_type, exc_val, exc_tb) -> None:
           # Neo4j driver handles commit/rollback automatically
           pass
           
       def run(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
           """Run a query in this transaction."""
           result = self._tx.run(query, params or {})
           return [dict(record) for record in result]
   
   class Neo4jGraphStorage:
       """Neo4j implementation of the GraphStorage protocol."""
       
       def __init__(self, uri: str, username: str, password: Optional[str] = None, 
                    database: str = "neo4j", connection_timeout: int = 30,
                    max_connection_pool_size: int = 50):
           self.uri = uri
           self.username = username
           self.password = password
           self.database = database
           self.connection_timeout = connection_timeout
           self.max_connection_pool_size = max_connection_pool_size
           self.driver = None
           
       def connect(self) -> None:
           """Establish connection to Neo4j."""
           if self.driver is not None:
               return
               
           self.driver = GraphDatabase.driver(
               self.uri,
               auth=(self.username, self.password),
               max_connection_pool_size=self.max_connection_pool_size,
               connection_timeout=self.connection_timeout
           )
           
           # Test connection
           with self.driver.session(database=self.database) as session:
               session.run("RETURN 1").single()
               
       def disconnect(self) -> None:
           """Close connection to Neo4j."""
           if self.driver is not None:
               self.driver.close()
               self.driver = None
               
       def is_connected(self) -> bool:
           """Check if connected to Neo4j."""
           if self.driver is None:
               return False
               
           try:
               with self.driver.session(database=self.database) as session:
                   session.run("RETURN 1").single()
                   return True
           except Exception:
               return False
               
       def create_node(self, label: str, properties: Dict[str, Any]) -> str:
           """Create a new node in Neo4j."""
           if self.driver is None:
               self.connect()
               
           query = f"""
           CREATE (n:{label} $properties)
           RETURN id(n) as id, n
           """
           
           with self.driver.session(database=self.database) as session:
               result = session.run(query, {"properties": properties})
               record = result.single()
               return str(record["id"])
           
       # Implement remaining methods similarly...
   ```

3. **Implement SQLite Adapter**:
   
   Create a relational schema for graph representation in SQLite and implement the graph operations.
   
   ```python
   import sqlite3
   import json
   import uuid
   from typing import Any, Dict, List, Optional, Callable, TypeVar
   from contextlib import contextmanager
   
   T = TypeVar('T')
   
   class SQLiteTransaction:
       """SQLite transaction wrapper."""
       
       def __init__(self, connection: sqlite3.Connection):
           self.connection = connection
           
       def commit(self) -> None:
           """Commit the transaction."""
           self.connection.commit()
           
       def rollback(self) -> None:
           """Rollback the transaction."""
           self.connection.rollback()
           
       def __enter__(self) -> 'SQLiteTransaction':
           return self
           
       def __exit__(self, exc_type, exc_val, exc_tb) -> None:
           if exc_type is not None:
               self.rollback()
           else:
               self.commit()
               
       def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> sqlite3.Cursor:
           """Execute a query in this transaction."""
           return self.connection.execute(query, params or {})
           
       def executemany(self, query: str, params_seq: List[Dict[str, Any]]) -> sqlite3.Cursor:
           """Execute a query multiple times with different parameters."""
           return self.connection.executemany(query, params_seq)
   
   class SQLiteGraphStorage:
       """SQLite implementation of the GraphStorage protocol."""
       
       def __init__(self, db_path: str):
           self.db_path = db_path
           self.connection = None
           self._setup_db()
           
       def _setup_db(self) -> None:
           """Set up the database schema if it doesn't exist."""
           self.connect()
           
           # Create schema if it doesn't exist
           with self.begin_transaction() as tx:
               # Nodes table
               tx.execute("""
               CREATE TABLE IF NOT EXISTS nodes (
                   id TEXT PRIMARY KEY,
                   label TEXT NOT NULL,
                   properties TEXT NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
               )
               """)
               
               # Create index on label for faster lookups
               tx.execute("CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label)")
               
               # Relationships table
               tx.execute("""
               CREATE TABLE IF NOT EXISTS relationships (
                   id TEXT PRIMARY KEY,
                   start_node_id TEXT NOT NULL,
                   end_node_id TEXT NOT NULL,
                   type TEXT NOT NULL,
                   properties TEXT NOT NULL,
                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                   FOREIGN KEY (start_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
                   FOREIGN KEY (end_node_id) REFERENCES nodes(id) ON DELETE CASCADE
               )
               """)
               
               # Create indexes for faster relationship lookups
               tx.execute("CREATE INDEX IF NOT EXISTS idx_rel_start ON relationships(start_node_id)")
               tx.execute("CREATE INDEX IF NOT EXISTS idx_rel_end ON relationships(end_node_id)")
               tx.execute("CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(type)")
           
       def connect(self) -> None:
           """Connect to SQLite database."""
           if self.connection is not None:
               return
               
           self.connection = sqlite3.connect(self.db_path)
           self.connection.row_factory = sqlite3.Row
           
           # Enable foreign keys
           self.connection.execute("PRAGMA foreign_keys = ON")
           
       def disconnect(self) -> None:
           """Disconnect from SQLite database."""
           if self.connection is not None:
               self.connection.close()
               self.connection = None
               
       def is_connected(self) -> bool:
           """Check if connected to SQLite database."""
           if self.connection is None:
               return False
               
           try:
               self.connection.execute("SELECT 1")
               return True
           except Exception:
               return False
               
       def create_node(self, label: str, properties: Dict[str, Any]) -> str:
           """Create a new node in SQLite."""
           if self.connection is None:
               self.connect()
               
           node_id = str(uuid.uuid4())
           
           with self.begin_transaction() as tx:
               tx.execute(
                   "INSERT INTO nodes (id, label, properties) VALUES (?, ?, ?)",
                   (node_id, label, json.dumps(properties))
               )
               
           return node_id
           
       # Implement remaining methods similarly...
       
       def query(self, query_string: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
           """Execute a Cypher-like query against SQLite.
           
           This is a simplified implementation that supports basic operations.
           A full implementation would need a proper Cypher to SQL translator.
           """
           # This is where we would use a query translation layer
           # For now, just support some basic patterns
           
           if self.connection is None:
               self.connect()
               
           params = params or {}
           
           # Handle some common query patterns
           if query_string.startswith("MATCH (n:") and "RETURN n" in query_string:
               # Extract label from pattern like MATCH (n:Label) RETURN n
               import re
               label_match = re.search(r"MATCH \(n:(\w+)\)", query_string)
               if label_match:
                   label = label_match.group(1)
                   cursor = self.connection.execute(
                       "SELECT id, label, properties FROM nodes WHERE label = ?",
                       (label,)
                   )
                   return [
                       {
                           "n": {
                               "id": row["id"],
                               "label": row["label"],
                               "properties": json.loads(row["properties"])
                           }
                       }
                       for row in cursor.fetchall()
                   ]
           
           # Fallback for unsupported queries
           raise NotImplementedError(f"Query not supported: {query_string}")
   ```

4. **Create Factory for Storage Selection**:
   
   Implement a factory function that creates the appropriate storage implementation based on configuration.
   
   ```python
   from typing import Dict, Any, Optional
   from pathlib import Path
   
   def get_storage(config: Dict[str, Any]) -> 'GraphStorage':
       """Create a storage instance based on configuration.
       
       Args:
           config: Configuration dictionary with storage settings
           
       Returns:
           Configured GraphStorage implementation
           
       Raises:
           ValueError: If storage type is unsupported
       """
       storage_type = config.get("storage", {}).get("type", "sqlite")
       
       if storage_type == "sqlite":
           db_path = config.get("storage", {}).get("path", "codestory.db")
           # Ensure path is absolute
           if not Path(db_path).is_absolute():
               db_path = str(Path.cwd() / db_path)
           return SQLiteGraphStorage(db_path)
           
       elif storage_type == "neo4j":
           uri = config.get("storage", {}).get("uri")
           if not uri:
               raise ValueError("Neo4j URI is required")
               
           username = config.get("storage", {}).get("username", "neo4j")
           password = config.get("storage", {}).get("password")
           database = config.get("storage", {}).get("database", "neo4j")
           connection_timeout = config.get("storage", {}).get("connection_timeout", 30)
           max_connection_pool_size = config.get("storage", {}).get("max_connection_pool_size", 50)
           
           return Neo4jGraphStorage(
               uri=uri,
               username=username,
               password=password,
               database=database,
               connection_timeout=connection_timeout,
               max_connection_pool_size=max_connection_pool_size
           )
           
       elif storage_type == "neo4j_embedded":
           # Future implementation
           raise NotImplementedError("Neo4j embedded mode not yet implemented")
           
       else:
           raise ValueError(f"Unsupported storage type: {storage_type}")
   ```

5. **Update Existing Code to Use Storage Interface**:
   
   Modify pipeline steps and other components to use the abstraction layer instead of direct Neo4j access.
   
   Example of updating a pipeline step:
   
   ```python
   # Before:
   def process_file(self, file_path, neo4j_connector):
       # Direct Neo4j operations
       query = "MATCH (n:File) WHERE n.path = $path RETURN n"
       result = neo4j_connector.query(query, {"path": str(file_path)})
       # ...
   
   # After:
   def process_file(self, file_path, storage: GraphStorage):
       # Abstract storage operations
       node = storage.get_nodes_by_label("File", {"path": str(file_path)})
       if not node:
           node_id = storage.create_node("File", {"path": str(file_path)})
       else:
           node_id = node[0]["id"]
       # ...
   ```

#### Validation Steps:

1. **Unit Tests**: Create comprehensive tests for both storage implementations
   ```bash
   pytest tests/unit/storage/test_sqlite_storage.py tests/unit/storage/test_neo4j_storage.py
   ```

2. **Integration Test**: Verify that pipeline steps work with both backends
   ```bash
   pytest tests/integration/test_pipeline_with_sqlite.py
   ```

3. **Performance Comparison**: Benchmark SQLite vs Neo4j for common operations
   ```bash
   python -m codestory.tools.benchmark_storage
   ```

#### Success Criteria:

- All unit tests pass for both storage implementations
- Integration tests pass with both backends
- Performance metrics show acceptable performance for local development
- No code directly accesses Neo4j, only through the abstraction layer

### Phase 2: Processing Simplification

**Goal**: Replace Celery-based task processing with direct execution for local development, simplifying the architecture while maintaining the ability to scale up when needed.

#### Tasks:

1. **Create Processing Engine Interface**:
   
   Define a comprehensive interface for processing operations that abstracts the execution details.
   
   ```python
   from datetime import datetime
   from enum import Enum
   from typing import Any, Dict, List, Optional, Protocol, Union
   from uuid import uuid4
   
   class JobStatus(Enum):
       """Possible job status values."""
       PENDING = "PENDING"
       RUNNING = "RUNNING"
       SUCCEEDED = "SUCCEEDED"
       FAILED = "FAILED"
       CANCELLED = "CANCELLED"
       TIMED_OUT = "TIMED_OUT"
   
   class JobStatusInfo:
       """Information about a job's status."""
       job_id: str
       status: JobStatus
       step_name: str
       repository_path: str
       start_time: Optional[datetime]
       end_time: Optional[datetime]
       progress: float  # 0.0 to 1.0
       message: Optional[str]
       error: Optional[str]
       result: Optional[Dict[str, Any]]
       metadata: Dict[str, Any]
   
       def to_dict(self) -> Dict[str, Any]:
           """Convert job status to dictionary."""
           return {
               "job_id": self.job_id,
               "status": self.status.value,
               "step_name": self.step_name,
               "repository_path": self.repository_path,
               "start_time": self.start_time.isoformat() if self.start_time else None,
               "end_time": self.end_time.isoformat() if self.end_time else None,
               "progress": self.progress,
               "message": self.message,
               "error": self.error,
               "result": self.result,
               "metadata": self.metadata
           }
   
   class ProcessingEngine(Protocol):
       """Interface for processing engines."""
       
       def execute_step(self, step_name: str, repository_path: str, 
                       **config) -> Dict[str, Any]:
           """Execute a single pipeline step.
           
           Args:
               step_name: Name of the step to execute
               repository_path: Path to the repository
               config: Step-specific configuration
               
           Returns:
               Dictionary with execution result including job_id
           """
           
       def execute_pipeline(self, repository_path: str, 
                           steps: List[Dict[str, Any]]) -> Dict[str, Any]:
           """Execute a sequence of pipeline steps.
           
           Args:
               repository_path: Path to the repository
               steps: List of step configurations
               
           Returns:
               Dictionary with execution result including job_id
           """
           
       def get_status(self, job_id: str) -> JobStatusInfo:
           """Get the status of a job.
           
           Args:
               job_id: Unique job identifier
               
           Returns:
               Job status information
           """
           
       def cancel_job(self, job_id: str) -> JobStatusInfo:
           """Cancel a running job.
           
           Args:
               job_id: Unique job identifier
               
           Returns:
               Updated job status information
           """
           
       def list_jobs(self, status: Optional[JobStatus] = None, 
                   limit: int = 100) -> List[JobStatusInfo]:
           """List jobs with optional status filter.
           
           Args:
               status: Optional status filter
               limit: Maximum number of jobs to return
               
           Returns:
               List of job status information
           """
   ```

2. **Implement Direct Execution Engine**:
   
   Create a synchronous execution engine that runs pipeline steps directly in the current process.
   
   ```python
   from datetime import datetime
   import threading
   import time
   import uuid
   from typing import Any, Dict, List, Optional, Set, Callable
   import traceback
   import logging
   
   logger = logging.getLogger(__name__)
   
   class JobTracker:
       """Tracks job status and progress."""
       
       def __init__(self):
           self._jobs: Dict[str, JobStatusInfo] = {}
           self._lock = threading.Lock()
           
       def create_job(self, step_name: str, repository_path: str) -> str:
           """Create a new job and return its ID."""
           job_id = str(uuid.uuid4())
           
           job_info = JobStatusInfo(
               job_id=job_id,
               status=JobStatus.PENDING,
               step_name=step_name,
               repository_path=repository_path,
               start_time=None,
               end_time=None,
               progress=0.0,
               message="Job created",
               error=None,
               result=None,
               metadata={}
           )
           
           with self._lock:
               self._jobs[job_id] = job_info
               
           return job_id
           
       def get_job(self, job_id: str) -> Optional[JobStatusInfo]:
           """Get job status by ID."""
           with self._lock:
               return self._jobs.get(job_id)
               
       def update_job(self, job_id: str, **kwargs) -> None:
           """Update job status."""
           with self._lock:
               job = self._jobs.get(job_id)
               if job:
                   for key, value in kwargs.items():
                       setattr(job, key, value)
                       
       def list_jobs(self, status: Optional[JobStatus] = None, 
                    limit: int = 100) -> List[JobStatusInfo]:
           """List jobs with optional status filter."""
           with self._lock:
               jobs = list(self._jobs.values())
               
           if status:
               jobs = [job for job in jobs if job.status == status]
               
           # Sort by start time descending
           jobs.sort(key=lambda job: job.start_time if job.start_time else datetime.min,
                    reverse=True)
                    
           return jobs[:limit]
           
       def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
           """Remove old completed jobs."""
           cutoff = datetime.now() - timedelta(hours=max_age_hours)
           removed = 0
           
           with self._lock:
               for job_id in list(self._jobs.keys()):
                   job = self._jobs[job_id]
                   if (job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED) and
                       job.end_time and job.end_time < cutoff):
                       del self._jobs[job_id]
                       removed += 1
                       
           return removed
   
   class DirectProcessingEngine:
       """Direct execution engine for pipeline steps."""
       
       def __init__(self):
           self._tracker = JobTracker()
           self._cancel_events: Dict[str, threading.Event] = {}
           self._step_registry: Dict[str, Callable] = {}
           self._running_threads: Dict[str, threading.Thread] = {}
           self._lock = threading.Lock()
           
       def register_step(self, name: str, step_func: Callable) -> None:
           """Register a pipeline step function."""
           self._step_registry[name] = step_func
           
       def execute_step(self, step_name: str, repository_path: str, 
                       **config) -> Dict[str, Any]:
           """Execute a single pipeline step."""
           if step_name not in self._step_registry:
               raise ValueError(f"Unknown step: {step_name}")
               
           step_func = self._step_registry[step_name]
           job_id = self._tracker.create_job(step_name, repository_path)
           cancel_event = threading.Event()
           
           with self._lock:
               self._cancel_events[job_id] = cancel_event
           
           # Define the worker function that will run in a thread
           def worker():
               self._tracker.update_job(
                   job_id,
                   status=JobStatus.RUNNING,
                   start_time=datetime.now(),
                   message="Job started"
               )
               
               try:
                   # Create a progress callback
                   def progress_callback(progress: float, message: str = None):
                       self._tracker.update_job(
                           job_id,
                           progress=progress,
                           message=message if message else f"Progress: {progress:.1%}"
                       )
                   
                   # Execute the step function
                   result = step_func(
                       repository_path=repository_path,
                       job_id=job_id,
                       cancel_event=cancel_event,
                       progress_callback=progress_callback,
                       **config
                   )
                   
                   self._tracker.update_job(
                       job_id,
                       status=JobStatus.SUCCEEDED,
                       end_time=datetime.now(),
                       progress=1.0,
                       message="Job completed successfully",
                       result=result
                   )
                   
               except Exception as e:
                   logger.exception(f"Error executing step {step_name}")
                   self._tracker.update_job(
                       job_id,
                       status=JobStatus.FAILED,
                       end_time=datetime.now(),
                       message=f"Job failed: {str(e)}",
                       error=f"{str(e)}\n{traceback.format_exc()}"
                   )
               finally:
                   with self._lock:
                       if job_id in self._running_threads:
                           del self._running_threads[job_id]
                       if job_id in self._cancel_events:
                           del self._cancel_events[job_id]
           
           # Start the worker thread
           thread = threading.Thread(target=worker)
           thread.daemon = True
           
           with self._lock:
               self._running_threads[job_id] = thread
               
           thread.start()
           
           return {
               "job_id": job_id,
               "status": "PENDING",
               "message": "Job started"
           }
           
       def execute_pipeline(self, repository_path: str, 
                           steps: List[Dict[str, Any]]) -> Dict[str, Any]:
           """Execute a sequence of pipeline steps."""
           # In the simple version, we'll just start the first step
           # and let the steps chain to each other
           if not steps:
               raise ValueError("No steps provided")
               
           first_step = steps[0]
           step_name = first_step.get("name")
           step_config = first_step.get("config", {})
           
           # Store the full pipeline in the job metadata
           job_result = self.execute_step(
               step_name=step_name,
               repository_path=repository_path,
               pipeline_steps=steps,
               current_step_index=0,
               **step_config
           )
           
           return job_result
           
       def get_status(self, job_id: str) -> JobStatusInfo:
           """Get the status of a job."""
           job_info = self._tracker.get_job(job_id)
           if not job_info:
               raise ValueError(f"Unknown job: {job_id}")
               
           return job_info
           
       def cancel_job(self, job_id: str) -> JobStatusInfo:
           """Cancel a running job."""
           job_info = self._tracker.get_job(job_id)
           if not job_info:
               raise ValueError(f"Unknown job: {job_id}")
               
           if job_info.status not in (JobStatus.PENDING, JobStatus.RUNNING):
               return job_info  # Already completed
               
           with self._lock:
               cancel_event = self._cancel_events.get(job_id)
               
           if cancel_event:
               cancel_event.set()
               
           self._tracker.update_job(
               job_id,
               status=JobStatus.CANCELLED,
               end_time=datetime.now(),
               message="Job cancelled by user"
           )
           
           return self._tracker.get_job(job_id)
           
       def list_jobs(self, status: Optional[JobStatus] = None, 
                   limit: int = 100) -> List[JobStatusInfo]:
           """List jobs with optional status filter."""
           return self._tracker.list_jobs(status, limit)
   ```

3. **Implement Celery Adapter** (for backward compatibility):
   
   Create a wrapper around existing Celery tasks that implements the ProcessingEngine interface.
   
   ```python
   from celery import Celery
   from celery.result import AsyncResult
   from datetime import datetime
   from typing import Any, Dict, List, Optional
   import json
   
   class CeleryProcessingEngine:
       """Celery-based processing engine for pipeline steps."""
       
       def __init__(self, broker_url: str, backend_url: str, 
                   app_name: str = "codestory"):
           self.app = Celery(
               app_name,
               broker=broker_url,
               backend=backend_url
           )
           
       def execute_step(self, step_name: str, repository_path: str, 
                       **config) -> Dict[str, Any]:
           """Execute a single pipeline step using Celery."""
           # Convert to the format expected by Celery tasks
           celery_task_name = f"codestory.tasks.{step_name}"
           
           # Prepare task arguments
           task_args = {
               "repository_path": repository_path,
               **config
           }
           
           # Send task to Celery
           result = self.app.send_task(
               celery_task_name,
               kwargs=task_args,
               countdown=0
           )
           
           return {
               "job_id": result.id,
               "status": "PENDING",
               "message": f"Job submitted to Celery: {result.id}"
           }
           
       def execute_pipeline(self, repository_path: str, 
                           steps: List[Dict[str, Any]]) -> Dict[str, Any]:
           """Execute a pipeline using Celery chain."""
           from celery import chain
           
           if not steps:
               raise ValueError("No steps provided")
               
           # Build a chain of tasks
           tasks = []
           for step in steps:
               step_name = step.get("name")
               step_config = step.get("config", {})
               
               celery_task_name = f"codestory.tasks.{step_name}"
               task_args = {
                   "repository_path": repository_path,
                   **step_config
               }
               
               tasks.append(self.app.signature(
                   celery_task_name,
                   kwargs=task_args
               ))
               
           # Execute the chain
           result = chain(*tasks).apply_async()
           
           return {
               "job_id": result.id,
               "status": "PENDING",
               "message": f"Pipeline submitted to Celery: {result.id}"
           }
           
       def get_status(self, job_id: str) -> JobStatusInfo:
           """Get job status from Celery."""
           result = AsyncResult(job_id, app=self.app)
           
           # Map Celery states to our states
           state_map = {
               "PENDING": JobStatus.PENDING,
               "STARTED": JobStatus.RUNNING,
               "SUCCESS": JobStatus.SUCCEEDED,
               "FAILURE": JobStatus.FAILED,
               "REVOKED": JobStatus.CANCELLED,
               "RETRY": JobStatus.RUNNING
           }
           
           status = state_map.get(result.state, JobStatus.PENDING)
           
           # Extract info from result metadata
           try:
               if result.result and isinstance(result.result, dict):
                   task_meta = result.result
               elif hasattr(result, "info") and result.info:
                   task_meta = result.info if isinstance(result.info, dict) else {}
               else:
                   task_meta = {}
           except Exception:
               task_meta = {}
               
           # Get metadata from backend
           task_meta = task_meta or {}
           
           # Create job status info
           info = JobStatusInfo(
               job_id=job_id,
               status=status,
               step_name=task_meta.get("task", "unknown"),
               repository_path=task_meta.get("repository_path", ""),
               start_time=datetime.fromisoformat(task_meta.get("start_time")) if task_meta.get("start_time") else None,
               end_time=datetime.fromisoformat(task_meta.get("end_time")) if task_meta.get("end_time") else None,
               progress=float(task_meta.get("progress", 0.0)),
               message=task_meta.get("message", f"Task state: {result.state}"),
               error=str(result.result) if status == JobStatus.FAILED and isinstance(result.result, Exception) else None,
               result=task_meta.get("result"),
               metadata=task_meta
           )
           
           return info
           
       def cancel_job(self, job_id: str) -> JobStatusInfo:
           """Cancel a Celery task."""
           self.app.control.revoke(job_id, terminate=True)
           
           # Get updated status
           info = self.get_status(job_id)
           
           # Force status to CANCELLED
           info.status = JobStatus.CANCELLED
           info.message = "Job cancelled by user"
           info.end_time = datetime.now()
           
           return info
           
       def list_jobs(self, status: Optional[JobStatus] = None, 
                   limit: int = 100) -> List[JobStatusInfo]:
           """List jobs from Celery backend.
           
           Note: This is limited by what Celery's backend provides.
           Redis and other backends might have different capabilities.
           """
           # This is a simplified implementation
           # A real implementation would need to query the backend
           # and might be backend-specific
           
           # For demonstration, we'll return an empty list
           # as Celery doesn't provide a standard way to list all tasks
           return []
   ```

4. **Create Factory for Engine Selection**:
   
   Implement a factory function that creates the appropriate processing engine based on configuration.
   
   ```python
   from typing import Dict, Any
   
   def get_processing_engine(config: Dict[str, Any]) -> 'ProcessingEngine':
       """Create a processing engine based on configuration.
       
       Args:
           config: Configuration dictionary with processing settings
           
       Returns:
           Configured ProcessingEngine implementation
           
       Raises:
           ValueError: If engine type is unsupported
       """
       engine_type = config.get("processing", {}).get("engine", "direct")
       
       if engine_type == "direct":
           return DirectProcessingEngine()
           
       elif engine_type == "celery":
           broker_url = config.get("processing", {}).get("broker_url")
           if not broker_url:
               raise ValueError("Celery broker URL is required")
               
           backend_url = config.get("processing", {}).get("backend_url")
           if not backend_url:
               raise ValueError("Celery backend URL is required")
               
           app_name = config.get("app", {}).get("name", "codestory")
           
           return CeleryProcessingEngine(
               broker_url=broker_url,
               backend_url=backend_url,
               app_name=app_name
           )
           
       elif engine_type == "async":
           # Future implementation using asyncio
           raise NotImplementedError("Async processing engine not yet implemented")
           
       else:
           raise ValueError(f"Unsupported processing engine: {engine_type}")
   ```

5. **Update Pipeline Steps for Direct Execution**:
   
   Modify the pipeline step implementation to work with both execution engines.
   
   ```python
   # Example pipeline step implementation
   from pathlib import Path
   import threading
   from typing import Any, Callable, Dict, Optional
   
   class FileSystemStep:
       """Analyzes file system structure of a repository."""
       
       def __init__(self, storage):
           self.storage = storage
           
       def run(self, repository_path: str, job_id: str = None, 
              cancel_event: Optional[threading.Event] = None,
              progress_callback: Optional[Callable[[float, str], None]] = None,
              **config) -> Dict[str, Any]:
           """Run the file system analysis step.
           
           Args:
               repository_path: Path to the repository
               job_id: Unique job identifier
               cancel_event: Event to check for cancellation
               progress_callback: Function to report progress
               config: Additional configuration
               
           Returns:
               Result data
           """
           repo_path = Path(repository_path)
           if not repo_path.exists() or not repo_path.is_dir():
               raise ValueError(f"Invalid repository path: {repository_path}")
               
           # Create repository node
           repo_node_id = self.storage.create_node("Repository", {
               "path": str(repo_path),
               "name": repo_path.name
           })
           
           # Scan files
           all_files = list(repo_path.rglob("*"))
           file_count = len(all_files)
           processed = 0
           
           for file_path in all_files:
               # Check for cancellation
               if cancel_event and cancel_event.is_set():
                   return {"status": "cancelled", "message": "Operation cancelled"}
                   
               if file_path.is_file():
                   # Process file
                   rel_path = str(file_path.relative_to(repo_path))
                   
                   # Create file node
                   file_node_id = self.storage.create_node("File", {
                       "path": rel_path,
                       "name": file_path.name,
                       "size": file_path.stat().st_size,
                       "extension": file_path.suffix
                   })
                   
                   # Connect to repository
                   self.storage.create_relationship(
                       repo_node_id, file_node_id, "CONTAINS"
                   )
               
               # Update progress
               processed += 1
               if progress_callback:
                   progress = processed / file_count
                   progress_callback(progress, f"Processed {processed}/{file_count} files")
           
           return {
               "repository_id": repo_node_id,
               "file_count": processed
           }
   ```

6. **Update API Service to Use Processing Interface**:
   
   Modify the API endpoints to work with the processing abstraction layer.
   
   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   from typing import Dict, Any, List, Optional
   
   from ..dependencies import get_processing_engine, get_storage
   
   router = APIRouter(prefix="/api/v1")
   
   @router.post("/repositories/{repository_path:path}/ingest")
   async def start_ingestion(
       repository_path: str,
       steps: Optional[List[str]] = Query(None),
       processing_engine = Depends(get_processing_engine)
   ) -> Dict[str, Any]:
       """Start ingestion for a repository."""
       # Convert path to absolute if needed
       if not Path(repository_path).is_absolute():
           repository_path = str(Path.cwd() / repository_path)
           
       # Get default steps if not specified
       if not steps:
           steps = ["filesystem", "blarify", "summarizer", "docgrapher"]
           
       # Convert to step configurations
       step_configs = [{"name": step, "config": {}} for step in steps]
       
       # Start pipeline execution
       result = processing_engine.execute_pipeline(
           repository_path=repository_path,
           steps=step_configs
       )
       
       return {
           "job_id": result["job_id"],
           "status": result["status"],
           "message": result["message"]
       }
   
   @router.get("/jobs/{job_id}")
   async def get_job_status(
       job_id: str,
       processing_engine = Depends(get_processing_engine)
   ) -> Dict[str, Any]:
       """Get status of a job."""
       try:
           status = processing_engine.get_status(job_id)
           return status.to_dict()
       except ValueError as e:
           raise HTTPException(status_code=404, detail=str(e))
   
   @router.post("/jobs/{job_id}/cancel")
   async def cancel_job(
       job_id: str,
       processing_engine = Depends(get_processing_engine)
   ) -> Dict[str, Any]:
       """Cancel a job."""
       try:
           status = processing_engine.cancel_job(job_id)
           return status.to_dict()
       except ValueError as e:
           raise HTTPException(status_code=404, detail=str(e))
   ```

#### Validation Steps:

1. **Unit Tests**: Create tests for both processing engines
   ```bash
   pytest tests/unit/processing/test_direct_engine.py tests/unit/processing/test_celery_engine.py
   ```

2. **Integration Tests**: Verify pipeline execution with both engines
   ```bash
   pytest tests/integration/test_pipeline_execution.py
   ```

3. **Performance Tests**: Compare direct vs. Celery execution performance
   ```bash
   python -m codestory.tools.benchmark_processing
   ```

4. **Manual Testing**: Verify API endpoints work with both engines
   ```bash
   # Direct mode
   curl -X POST "http://localhost:8000/api/v1/repositories/path/to/repo/ingest"
   
   # Get status
   curl "http://localhost:8000/api/v1/jobs/{job_id}"
   ```

#### Success Criteria:

- All unit tests pass for both processing engines
- Integration tests pass with both engines
- Performance metrics show improved performance for local development
- API endpoints work consistently with both engines
- No direct Celery dependencies in application code
- Transition is transparent to users of the API

### Phase 3: Configuration Simplification

**Goal**: Create a simplified configuration system with a single source of truth.

#### Tasks:

1. **Define New Configuration Schema**:
   - Create Pydantic model for new configuration
   - Implement validation and type checking
   - Add support for environment variable substitution

2. **Create Migration Utility**:
   - Tool to convert existing configs to new format
   - Documentation for configuration changes

3. **Update Components to Use New Configuration**:
   - Modify all components to use the new configuration
   - Add backward compatibility where needed

4. **Simplify Environment Setup**:
   - Create helper scripts for local development
   - Add development presets for quick setup

### Phase 4: User Interface Updates

**Goal**: Update user interfaces to work with the simplified architecture.

#### Tasks:

1. **Update CLI**:
   - Modify CLI to use new abstractions
   - Add direct component access for improved performance
   - Maintain existing command structure for compatibility

2. **Simplify GUI**:
   - Update API client to work with new endpoints
   - Optimize for local development
   - Add offline capabilities where possible

3. **Create Local Development Mode**:
   - Single-command startup for all components
   - Integrated debugging support
   - Live reloading for code changes

### Phase 5: Testing and Documentation

**Goal**: Update tests and documentation to reflect the new architecture.

#### Tasks:

1. **Update Unit Tests**:
   - Modify tests to use new abstractions
   - Add tests for new components
   - Simplify test fixtures

2. **Simplify Integration Tests**:
   - Remove dependency on containers for basic tests
   - Create lightweight test environment
   - Add container-based tests as optional

3. **Update Documentation**:
   - Create new architectural diagrams
   - Update developer guides
   - Add migration guides for existing users

## Implementation Timeline

- **Phase 1: Storage Abstraction** - 2 weeks
- **Phase 2: Processing Simplification** - 2 weeks
- **Phase 3: Configuration Simplification** - 1 week
- **Phase 4: User Interface Updates** - 2 weeks
- **Phase 5: Testing and Documentation** - 1 week

Total estimated timeline: 8 weeks for full transition.

## Compatibility Strategy

To ensure a smooth transition, we'll maintain backward compatibility:

1. **Feature Flags**: Add flags to enable/disable new components
2. **Gradual Adoption**: Allow mixing old and new components during transition
3. **Compatibility Layers**: Create adapters for integrating new and old code
4. **Documentation**: Provide clear guidance for migration

## Proof of Concept

As an initial proof of concept, we can implement:

1. SQLite-based graph storage adapter
2. Direct execution engine for a single pipeline step
3. Simplified configuration loader

This will demonstrate the viability of the approach and provide early feedback for the full implementation.

## Success Criteria

The implementation will be considered successful when:

1. The system can run entirely without Docker containers
2. Startup time is reduced to under 10 seconds
3. Resource usage is reduced by at least 50%
4. All tests pass with the new architecture
5. Existing functionality is maintained
6. Documentation is updated to reflect the new architecture

## Conclusion

This implementation plan provides a practical path to transition from the current architecture to a simplified, modular architecture optimized for local development. The phased approach ensures that functionality is maintained throughout the process, while the abstractions allow for flexibility in implementation details.
