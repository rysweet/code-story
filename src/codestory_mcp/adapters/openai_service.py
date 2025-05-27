"""Adapter for the OpenAI client.

This module provides an adapter for interacting with the OpenAI client.
"""

import time
from functools import lru_cache
from typing import Any

import structlog
from fastapi import status

from codestory.llm.client import OpenAIClient
from codestory.llm.models import ChatCompletionRequest, ChatMessage
from codestory_mcp.tools.base import ToolError
from codestory_mcp.utils.metrics import get_metrics

logger = structlog.get_logger(__name__)


class OpenAIServiceAdapter:
    """Adapter for the OpenAI client."""

    def __init__(self, client: OpenAIClient | None = None) -> None:
        """Initialize the adapter.

        Args:
            client: Optional OpenAI client
        """
        self.client = client or OpenAIClient()
        self.metrics = get_metrics()

    async def generate_code_summary(
        self, code: str, context: str | None = None, max_tokens: int = 500
    ) -> str:
        """Generate a summary of a code snippet.

        Args:
            code: Code snippet to summarize
            context: Optional context for the code snippet
            max_tokens: Maximum tokens in the response

        Returns:
            Summary of the code snippet

        Raises:
            ToolError: If summarization fails
        """
        start_time = time.time()

        try:
            # Create prompt
            messages = [
                ChatMessage(
                    role="system",
                    content=(
                        "You are a helpful assistant that summarizes code. "
                        "Provide a clear, concise explanation of what the code does, "
                        "focusing on its purpose, functionality, and key components. "
                        "Be specific and technical, but avoid unnecessary details."
                    ),
                )
            ]

            # Add context if provided
            if context:
                messages.append(
                    ChatMessage(
                        role="user",
                        content=(
                            f"I need to understand this code in the context of: {context}\n\n"
                            "Please summarize what it does, its main purpose, and how it works."
                        ),
                    )
                )
            else:
                messages.append(
                    ChatMessage(
                        role="user",
                        content=(
                            "Please summarize what this code does, its main purpose, and how it works."
                        ),
                    )
                )

            # Add code
            messages.append(ChatMessage(role="user", content=f"```\n{code}\n```"))

            # Create request
            request = ChatCompletionRequest(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for more focused, deterministic responses
                model="gpt-4-turbo",  # Use latest GPT-4 model
            )

            # Get response
            response = await self.client.create_chat_completion(request)

            # Extract summary
            summary = response.choices[0].message.content

            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_service_api_call("openai_summary", "success", duration)

            return summary

        except Exception as e:
            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_service_api_call("openai_summary", "error", duration)

            # Log error
            logger.exception(
                "Code summarization failed",
                error=str(e),
            )

            # Raise tool error
            raise ToolError(
                f"Code summarization failed: {e!s}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    async def generate_path_explanation(
        self, path_elements: list[dict[str, Any]], max_tokens: int = 300
    ) -> str:
        """Generate an explanation of a path between nodes.

        Args:
            path_elements: List of path elements (nodes and relationships)
            max_tokens: Maximum tokens in the response

        Returns:
            Explanation of the path

        Raises:
            ToolError: If explanation generation fails
        """
        start_time = time.time()

        try:
            # Create path description
            path_description = ""

            for i, element in enumerate(path_elements):
                if element.get("element_type") == "node":
                    path_description += f"\nNode {i//2 + 1}: {element.get('name', 'Unknown')} (Type: {element.get('type', 'Unknown')})"
                    if "content" in element and len(element["content"]) < 200:
                        path_description += f"\nContent: {element['content'][:200]}..."
                else:  # relationship
                    path_description += f"\n--[{element.get('type', 'RELATED_TO')}]-->"

            # Create prompt
            messages = [
                ChatMessage(
                    role="system",
                    content=(
                        "You are a helpful assistant that explains relationships between code elements. "
                        "Based on the path between code elements, explain how they are related "
                        "and what this relationship means for the codebase."
                    ),
                ),
                ChatMessage(
                    role="user",
                    content=(
                        "Please explain the following path between code elements in a clear, "
                        "concise way. Focus on how these elements interact and what this "
                        "relationship reveals about the code structure and behavior.\n\n"
                        f"{path_description}"
                    ),
                ),
            ]

            # Create request
            request = ChatCompletionRequest(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
                model="gpt-4-turbo",
            )

            # Get response
            response = await self.client.create_chat_completion(request)

            # Extract explanation
            explanation = response.choices[0].message.content

            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_service_api_call(
                "openai_path_explanation", "success", duration
            )

            return explanation

        except Exception as e:
            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_service_api_call(
                "openai_path_explanation", "error", duration
            )

            # Log error
            logger.exception(
                "Path explanation failed",
                error=str(e),
            )

            # Raise tool error
            raise ToolError(
                f"Path explanation failed: {e!s}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

    async def find_similar_code(
        self, code: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Find semantically similar code.

        Args:
            code: Code snippet to find similar code for
            limit: Maximum number of results to return

        Returns:
            List of similar code elements with similarity scores

        Raises:
            ToolError: If similarity search fails
        """
        start_time = time.time()

        try:
            # Get embeddings for the code snippet
            await self.client.create_embedding(code)

            # Record metrics for embedding creation
            embedding_duration = time.time() - start_time
            self.metrics.record_service_api_call(
                "openai_embedding", "success", embedding_duration
            )

            # TODO: Implement vector search for similar code
            # This would typically use the embedding to search a vector index
            # For now, return a placeholder implementation

            # Mock results for similar code
            results = [
                {
                    "id": f"mock-{i}",
                    "type": "Function",
                    "name": f"similarFunction{i}",
                    "content": f"def similarFunction{i}():\n    print('Similar to provided code')",
                    "path": f"/path/to/file{i}.py",
                    "score": 1.0 - (i * 0.1),
                }
                for i in range(min(limit, 5))
            ]

            # Record metrics
            total_duration = time.time() - start_time
            self.metrics.record_service_api_call(
                "similar_code", "success", total_duration
            )
            self.metrics.record_graph_operation("similar_code")

            return results

        except Exception as e:
            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_service_api_call("similar_code", "error", duration)

            # Log error
            logger.exception(
                "Similar code search failed",
                error=str(e),
            )

            # Raise tool error
            raise ToolError(
                f"Similar code search failed: {e!s}",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )


@lru_cache
def get_openai_service() -> OpenAIServiceAdapter:
    """Get the OpenAI service adapter singleton.

    Returns:
        OpenAI service adapter
    """
    return OpenAIServiceAdapter()
