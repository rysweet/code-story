import os
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["CODESTORY_NEO4J__URI"] = "bolt://localhost:7687"
import pytest
from codestory_service.domain.ingestion import IngestionRequest, IngestionSourceType
from pydantic import ValidationError

def test_ingestion_request_local_path_valid():
    # This should match the CLI payload
    payload = {
        "source": "/repositories/repo",
        "source_type": IngestionSourceType.LOCAL_PATH,
        "priority": "default",
        "description": "CLI ingestion of repository: /repositories/repo"
    }
    try:
        req = IngestionRequest(**payload)
        print("IngestionRequest created successfully:", req)
    except ValidationError as e:
        print("ValidationError:", e)
        for err in e.errors():
            print("Error:", err)
        assert False, "IngestionRequest validation failed"

def test_ingestion_request_local_path_empty():
    # This should fail validation
    payload = {
        "source": "",
        "source_type": IngestionSourceType.LOCAL_PATH,
        "priority": "default",
        "description": "CLI ingestion of repository: (empty)"
    }
    with pytest.raises(ValidationError) as excinfo:
        IngestionRequest(**payload)
    print("Expected ValidationError:", excinfo.value)