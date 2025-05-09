#!/usr/bin/env python
"""Test script for the Ingestion Pipeline.

This script demonstrates how to use the PipelineManager to start and monitor
ingestion jobs.
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Add the source directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from codestory.ingestion_pipeline.manager import PipelineManager
from codestory.ingestion_pipeline.step import StepStatus
from codestory.config.settings import get_settings


def main():
    """Run a test of the ingestion pipeline."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the ingestion pipeline")
    parser.add_argument(
        "repository", 
        help="Path to the repository to process",
        type=Path
    )
    parser.add_argument(
        "--config", 
        help="Path to the pipeline configuration",
        default="pipeline_config.yml",
        type=Path
    )
    parser.add_argument(
        "--step",
        help="Run only a specific step (leave empty for full pipeline)",
        default=None
    )
    
    args = parser.parse_args()
    
    # Verify repository path
    if not args.repository.exists() or not args.repository.is_dir():
        print(f"Error: Repository path '{args.repository}' does not exist or is not a directory")
        return 1
    
    # Verify configuration path
    if not args.config.exists():
        print(f"Error: Configuration file '{args.config}' does not exist")
        return 1
    
    # Load settings to check configuration
    try:
        settings = get_settings()
        print(f"Using Neo4j at {settings.neo4j.uri}")
        print(f"Using Redis at {settings.redis.uri}")
    except Exception as e:
        print(f"Error loading settings: {e}")
        return 1
    
    # Create pipeline manager
    try:
        print(f"Loading pipeline configuration from {args.config}")
        manager = PipelineManager(config_path=args.config)
        
        if args.step:
            # Run a single step
            print(f"Running single step: {args.step}")
            step_class = manager._get_step_class(args.step)
            if not step_class:
                print(f"Error: Step '{args.step}' not found")
                return 1
            
            step = step_class()
            job_id = step.run(str(args.repository.absolute()))
            
            print(f"Started job: {job_id}")
            
            # Poll for status
            while True:
                status = step.status(job_id)
                print(f"Status: {status['status']}, Progress: {status.get('progress')}")
                
                if status["status"] in (StepStatus.COMPLETED, StepStatus.FAILED, 
                                      StepStatus.STOPPED, StepStatus.CANCELLED):
                    break
                
                time.sleep(2)
                
            # Final status
            if status["status"] == StepStatus.COMPLETED:
                print(f"✅ Step completed successfully!")
                if "result" in status:
                    print(f"Result: {status['result']}")
            else:
                print(f"❌ Step failed: {status.get('error', 'Unknown error')}")
                
        else:
            # Run full pipeline
            print(f"Starting ingestion pipeline for {args.repository}")
            job_id = manager.start_job(str(args.repository.absolute()))
            
            print(f"Started pipeline job: {job_id}")
            
            # Poll for status
            while True:
                status = manager.status(job_id)
                print(f"Status: {status['status']}")
                
                if status["status"] in (StepStatus.COMPLETED, StepStatus.FAILED, 
                                      StepStatus.STOPPED, StepStatus.CANCELLED):
                    break
                
                # If we have step results, show them
                if "steps" in status:
                    for i, step in enumerate(status["steps"]):
                        print(f"  Step {i+1} ({step['step']}): {step['status']}")
                
                time.sleep(5)
                
            # Final status
            if status["status"] == StepStatus.COMPLETED:
                print(f"✅ Pipeline completed successfully!")
            else:
                print(f"❌ Pipeline failed: {status.get('error', 'Unknown error')}")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())