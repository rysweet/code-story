import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
# This package contains tests for the codestory project.
# CLI contract: see tests/cli/test_cli.py for initial CLI interface contract and enforcement.
# Settings contract: see tests/config/test_settings.py for configuration contract and enforcement.
# GraphService contract: see tests/graph/test_graph_service.py for service interface contract and enforcement.
# AIClient contract: see tests/ai/test_ai_client.py for AI client interface contract and enforcement.
# MCPAdapter contract: see tests/mcp/test_mcp_adapter.py for MCP adapter interface contract and enforcement.
