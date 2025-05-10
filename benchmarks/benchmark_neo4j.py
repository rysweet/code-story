#!/usr/bin/env python3
"""
Performance benchmarks for Neo4j connector.

This script measures the performance of various operations through the Neo4jConnector
to help optimize configuration and identify bottlenecks.
"""

import os
import time
import random
import statistics
from typing import Dict, List, Any, Callable, Optional
import asyncio
import argparse
import json
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np

# Add the parent directory to the path to import from src
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from codestory.graphdb.neo4j_connector import Neo4jConnector


class Neo4jBenchmark:
    """Benchmark for Neo4j connector performance."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
        iterations: int = 100,
        concurrency: int = 10,
        output_dir: str = "./benchmark_results",
    ) -> None:
        """Initialize the benchmark.

        Args:
            uri: Neo4j connection URI
            username: Neo4j username
            password: Neo4j password
            database: Neo4j database name
            iterations: Number of iterations for each test
            concurrency: Maximum concurrent operations for async tests
            output_dir: Directory to store benchmark results
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.iterations = iterations
        self.concurrency = concurrency
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Create connector
        self.connector = Neo4jConnector(
            uri=uri, username=username, password=password, database=database
        )

        # Create async connector
        self.async_connector = Neo4jConnector(
            uri=uri,
            username=username,
            password=password,
            database=database,
            async_mode=True,
        )

        # Results storage
        self.results = {}

    def setup(self) -> None:
        """Set up the database for benchmarking."""
        print("Setting up benchmark database...")

        # Clear database
        self.connector.execute_query("MATCH (n) DETACH DELETE n", write=True)

        # Create test data
        print("Creating test data...")

        # Create nodes in batches
        batch_size = 1000
        total_nodes = 10000

        for i in tqdm(range(0, total_nodes, batch_size)):
            queries = []
            for j in range(batch_size):
                if i + j >= total_nodes:
                    break

                node_id = i + j
                queries.append(
                    {
                        "query": "CREATE (n:TestNode {id: $id, name: $name, value: $value}) RETURN n",
                        "params": {
                            "id": node_id,
                            "name": f"Node-{node_id}",
                            "value": random.random(),
                        },
                    }
                )

            self.connector.execute_many(queries)

        # Create relationships
        print("Creating relationships...")
        num_relationships = total_nodes * 2

        for i in tqdm(range(0, num_relationships, batch_size)):
            queries = []
            for j in range(batch_size):
                if i + j >= num_relationships:
                    break

                source_id = random.randint(0, total_nodes - 1)
                target_id = random.randint(0, total_nodes - 1)

                # Skip self-relationships
                if source_id == target_id:
                    target_id = (target_id + 1) % total_nodes

                queries.append(
                    {
                        "query": """
                    MATCH (s:TestNode {id: $source_id})
                    MATCH (t:TestNode {id: $target_id})
                    CREATE (s)-[r:RELATES_TO {id: $rel_id, strength: $strength}]->(t)
                    RETURN r
                    """,
                        "params": {
                            "source_id": source_id,
                            "target_id": target_id,
                            "rel_id": i + j,
                            "strength": random.random(),
                        },
                    }
                )

            self.connector.execute_many(queries)

        # Create indexes
        print("Creating indexes...")
        self.connector.execute_query(
            "CREATE INDEX test_node_id IF NOT EXISTS FOR (n:TestNode) ON (n.id)",
            write=True,
        )

        self.connector.execute_query(
            "CREATE INDEX test_node_name IF NOT EXISTS FOR (n:TestNode) ON (n.name)",
            write=True,
        )

        print("Setup complete!")

    def teardown(self) -> None:
        """Clean up the database after benchmarking."""
        print("Cleaning up...")

        # Drop indexes
        self.connector.execute_query("DROP INDEX test_node_id IF EXISTS", write=True)

        self.connector.execute_query("DROP INDEX test_node_name IF EXISTS", write=True)

        # Clear data
        self.connector.execute_query("MATCH (n:TestNode) DETACH DELETE n", write=True)

        # Close connections
        self.connector.close()

        print("Teardown complete!")

    def benchmark_sync_read(self) -> Dict[str, Any]:
        """Benchmark synchronous read operations."""
        print(f"Benchmarking synchronous read ({self.iterations} iterations)...")

        query = "MATCH (n:TestNode) WHERE n.id = $id RETURN n"
        durations = []

        for i in tqdm(range(self.iterations)):
            node_id = random.randint(0, 9999)

            start_time = time.time()
            self.connector.execute_query(query, {"id": node_id})
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        self.results["sync_read"] = stats
        return stats

    def benchmark_sync_write(self) -> Dict[str, Any]:
        """Benchmark synchronous write operations."""
        print(f"Benchmarking synchronous write ({self.iterations} iterations)...")

        query = """
        CREATE (n:TestNode {
            id: $id, 
            name: $name, 
            value: $value,
            timestamp: $timestamp
        })
        RETURN n
        """
        durations = []

        for i in tqdm(range(self.iterations)):
            node_id = 10000 + i

            start_time = time.time()
            self.connector.execute_query(
                query,
                {
                    "id": node_id,
                    "name": f"Benchmark-{node_id}",
                    "value": random.random(),
                    "timestamp": time.time(),
                },
                write=True,
            )
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        self.results["sync_write"] = stats
        return stats

    def benchmark_sync_transaction(self, batch_size: int = 10) -> Dict[str, Any]:
        """Benchmark synchronous transaction with multiple operations."""
        print(
            f"Benchmarking synchronous transactions ({self.iterations} iterations, batch size: {batch_size})..."
        )

        durations = []

        for i in tqdm(range(self.iterations)):
            queries = []

            for j in range(batch_size):
                node_id = 20000 + (i * batch_size) + j
                queries.append(
                    {
                        "query": "CREATE (n:TestNode {id: $id, name: $name}) RETURN n",
                        "params": {"id": node_id, "name": f"BatchNode-{node_id}"},
                    }
                )

            start_time = time.time()
            self.connector.execute_many(queries)
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        stats["operations_per_transaction"] = batch_size
        stats["operations_per_second"] = (
            stats["operations_per_transaction"] / stats["mean"]
        )

        self.results["sync_transaction"] = stats
        return stats

    async def benchmark_async_read(self) -> Dict[str, Any]:
        """Benchmark asynchronous read operations."""
        print(f"Benchmarking asynchronous read ({self.iterations} iterations)...")

        query = "MATCH (n:TestNode) WHERE n.id = $id RETURN n"
        durations = []

        for i in tqdm(range(self.iterations)):
            node_id = random.randint(0, 9999)

            start_time = time.time()
            await self.async_connector.execute_query_async(query, {"id": node_id})
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        self.results["async_read"] = stats
        return stats

    async def benchmark_concurrent_reads(self) -> Dict[str, Any]:
        """Benchmark concurrent asynchronous read operations."""
        print(
            f"Benchmarking concurrent reads ({self.iterations} iterations, concurrency: {self.concurrency})..."
        )

        query = "MATCH (n:TestNode) WHERE n.id = $id RETURN n"
        durations = []

        # Split into batches for progress tracking
        batch_size = min(100, self.iterations)
        for batch_start in tqdm(range(0, self.iterations, batch_size)):
            batch_end = min(batch_start + batch_size, self.iterations)
            batch_count = batch_end - batch_start

            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.concurrency)

            async def execute_with_semaphore() -> float:
                async with semaphore:
                    node_id = random.randint(0, 9999)
                    start_time = time.time()
                    await self.async_connector.execute_query_async(
                        query, {"id": node_id}
                    )
                    return time.time() - start_time

            # Create tasks for this batch
            tasks = [execute_with_semaphore() for _ in range(batch_count)]
            batch_durations = await asyncio.gather(*tasks)
            durations.extend(batch_durations)

        stats = self._calculate_stats(durations)
        stats["concurrency"] = self.concurrency
        stats["operations_per_second"] = self.concurrency / stats["mean"]

        self.results["concurrent_reads"] = stats
        return stats

    async def benchmark_async_transaction(self, batch_size: int = 10) -> Dict[str, Any]:
        """Benchmark asynchronous transaction with multiple operations."""
        print(
            f"Benchmarking async transactions ({self.iterations} iterations, batch size: {batch_size})..."
        )

        durations = []

        for i in tqdm(range(self.iterations)):
            queries = []

            for j in range(batch_size):
                node_id = 40000 + (i * batch_size) + j
                queries.append(
                    {
                        "query": "CREATE (n:TestNode {id: $id, name: $name}) RETURN n",
                        "params": {"id": node_id, "name": f"AsyncBatch-{node_id}"},
                    }
                )

            start_time = time.time()
            await self.async_connector.execute_many_async(queries)
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        stats["operations_per_transaction"] = batch_size
        stats["operations_per_second"] = (
            stats["operations_per_transaction"] / stats["mean"]
        )

        self.results["async_transaction"] = stats
        return stats

    def benchmark_path_query(self) -> Dict[str, Any]:
        """Benchmark path traversal query (multi-hop relationships)."""
        print(f"Benchmarking path traversal ({self.iterations} iterations)...")

        query = """
        MATCH path = (n:TestNode)-[:RELATES_TO*1..3]->(m:TestNode)
        WHERE n.id = $id
        RETURN path
        LIMIT 10
        """
        durations = []

        for i in tqdm(range(self.iterations)):
            node_id = random.randint(0, 9999)

            start_time = time.time()
            self.connector.execute_query(query, {"id": node_id})
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        self.results["path_query"] = stats
        return stats

    def benchmark_aggregation_query(self) -> Dict[str, Any]:
        """Benchmark aggregation query."""
        print(f"Benchmarking aggregation query ({self.iterations} iterations)...")

        query = """
        MATCH (n:TestNode)-[r:RELATES_TO]->(m:TestNode)
        WITH n, count(r) AS rel_count, avg(r.strength) AS avg_strength
        WHERE rel_count > $min_count
        RETURN n.id, n.name, rel_count, avg_strength
        ORDER BY rel_count DESC
        LIMIT 10
        """
        durations = []

        for i in tqdm(range(self.iterations)):
            min_count = random.randint(1, 5)

            start_time = time.time()
            self.connector.execute_query(query, {"min_count": min_count})
            duration = time.time() - start_time

            durations.append(duration)

        stats = self._calculate_stats(durations)
        self.results["aggregation_query"] = stats
        return stats

    def _calculate_stats(self, durations: List[float]) -> Dict[str, float]:
        """Calculate statistics for the durations."""
        if not durations:
            return {}

        return {
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "min": min(durations),
            "max": max(durations),
            "p90": np.percentile(durations, 90),
            "p95": np.percentile(durations, 95),
            "p99": np.percentile(durations, 99),
            "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "sample_size": len(durations),
        }

    def generate_report(self) -> None:
        """Generate a report of the benchmark results."""
        if not self.results:
            print("No benchmark results to report.")
            return

        # Save results to JSON
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        json_path = os.path.join(self.output_dir, f"neo4j_benchmark_{timestamp}.json")

        with open(json_path, "w") as f:
            json.dump(
                {
                    "benchmark_config": {
                        "uri": self.uri,
                        "database": self.database,
                        "iterations": self.iterations,
                        "concurrency": self.concurrency,
                        "timestamp": timestamp,
                    },
                    "results": self.results,
                },
                f,
                indent=2,
            )

        print(f"Results saved to {json_path}")

        # Generate plots
        self._generate_plots(timestamp)

        # Print summary
        self._print_summary()

    def _generate_plots(self, timestamp: str) -> None:
        """Generate plots of the benchmark results."""
        # Create a bar chart comparing mean durations
        plt.figure(figsize=(12, 6))

        benchmark_types = list(self.results.keys())
        means = [result["mean"] for result in self.results.values()]

        # Sort by mean duration
        sorted_data = sorted(zip(benchmark_types, means), key=lambda x: x[1])
        benchmark_types = [data[0] for data in sorted_data]
        means = [data[1] for data in sorted_data]

        plt.bar(benchmark_types, means)
        plt.title("Mean Duration by Benchmark Type")
        plt.xlabel("Benchmark Type")
        plt.ylabel("Mean Duration (seconds)")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        # Add values on top of bars
        for i, value in enumerate(means):
            plt.text(i, value + 0.001, f"{value:.4f}", ha="center")

        # Save plot
        plot_path = os.path.join(self.output_dir, f"neo4j_benchmark_{timestamp}.png")
        plt.savefig(plot_path)
        print(f"Plot saved to {plot_path}")

    def _print_summary(self) -> None:
        """Print a summary of the benchmark results."""
        print("\n=== Benchmark Summary ===\n")

        headers = [
            "Test",
            "Mean (s)",
            "Median (s)",
            "Min (s)",
            "Max (s)",
            "P95 (s)",
            "Ops/sec",
        ]
        row_format = (
            "{:<20} {:<10.4f} {:<10.4f} {:<10.4f} {:<10.4f} {:<10.4f} {:<10.2f}"
        )

        print(" ".join(f"{h:<10}" for h in headers))
        print("-" * 80)

        for test_name, results in sorted(
            self.results.items(), key=lambda x: x[1]["mean"]
        ):
            ops_per_sec = 1.0 / results["mean"]
            if "operations_per_second" in results:
                ops_per_sec = results["operations_per_second"]

            print(
                row_format.format(
                    test_name,
                    results["mean"],
                    results["median"],
                    results["min"],
                    results["max"],
                    results["p95"],
                    ops_per_sec,
                )
            )

        print("\n")


async def main() -> None:
    """Run the Neo4j benchmark."""
    parser = argparse.ArgumentParser(description="Neo4j Connector Benchmark")
    parser.add_argument("--uri", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--username", default="neo4j", help="Neo4j username")
    parser.add_argument("--password", default="password", help="Neo4j password")
    parser.add_argument("--database", default="neo4j", help="Neo4j database name")
    parser.add_argument(
        "--iterations", type=int, default=100, help="Number of iterations"
    )
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrency level")
    parser.add_argument(
        "--output-dir", default="./benchmark_results", help="Output directory"
    )
    parser.add_argument("--skip-setup", action="store_true", help="Skip database setup")
    parser.add_argument(
        "--skip-teardown", action="store_true", help="Skip database teardown"
    )
    args = parser.parse_args()

    benchmark = Neo4jBenchmark(
        uri=args.uri,
        username=args.username,
        password=args.password,
        database=args.database,
        iterations=args.iterations,
        concurrency=args.concurrency,
        output_dir=args.output_dir,
    )

    try:
        if not args.skip_setup:
            benchmark.setup()

        # Run synchronous benchmarks
        benchmark.benchmark_sync_read()
        benchmark.benchmark_sync_write()
        benchmark.benchmark_sync_transaction()
        benchmark.benchmark_path_query()
        benchmark.benchmark_aggregation_query()

        # Run asynchronous benchmarks
        await benchmark.benchmark_async_read()
        await benchmark.benchmark_concurrent_reads()
        await benchmark.benchmark_async_transaction()

        # Generate report
        benchmark.generate_report()
    finally:
        if not args.skip_teardown:
            benchmark.teardown()


if __name__ == "__main__":
    asyncio.run(main())
