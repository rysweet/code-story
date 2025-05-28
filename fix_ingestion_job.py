#!/usr/bin/env python3
"""Fix IngestionJob constructor calls to include all required fields."""

import re
from pathlib import Path


def fix_ingestion_job_calls() -> None:
    """Fix IngestionJob constructor calls in celery_adapter.py."""
    file_path = Path("src/codestory_service/infrastructure/celery_adapter.py")
    
    with open(file_path, "r") as f:
        content = f.read()
    
    # Pattern to match IngestionJob constructor calls
    pattern = r'return IngestionJob\(\s*([^)]+)\s*\)'
    
    def replace_ingestion_job(match):
        """Replace IngestionJob call with all required fields."""
        current_args = match.group(1)
        
        # Check if required fields are missing
        required_fields = {
            'source': 'None',
            'source_type': 'None', 
            'branch': 'None',
            'started_at': 'None',
            'completed_at': 'None',
            'duration': 'None',
            'steps': 'None',
        }
        
        # Add missing fields
        args_lines = current_args.strip().split('\n')
        existing_fields = set()
        
        for line in args_lines:
            if '=' in line:
                field_name = line.split('=')[0].strip()
                existing_fields.add(field_name)
        
        # Add missing required fields
        for field, default_value in required_fields.items():
            if field not in existing_fields:
                args_lines.append(f"                    {field}={default_value},")
        
        # Reconstruct the call
        new_args = '\n'.join(args_lines)
        return f'return IngestionJob(\n{new_args}\n                )'
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_ingestion_job, content, flags=re.DOTALL)
    
    # Write back
    with open(file_path, "w") as f:
        f.write(new_content)
    
    print("Fixed IngestionJob constructor calls")


if __name__ == "__main__":
    fix_ingestion_job_calls()
