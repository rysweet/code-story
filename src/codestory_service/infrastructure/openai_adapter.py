"""OpenAI adapter for the Code Story Service.

This module provides a service-specific adapter for OpenAI operations,
building on the core OpenAI client with additional functionality required
by the service layer.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status

from codestory.llm.client import OpenAIClient
from codestory.llm.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    OpenAIError,
)
from codestory.llm.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
)

from ..domain.graph import AskRequest, AskAnswer, Reference, ReferenceType

# Set up logging
logger = logging.getLogger(__name__)


class OpenAIAdapter:
    """Adapter for OpenAI operations specific to the service layer.

    This class wraps the core OpenAIClient, providing methods that map
    directly to the service's use cases and handling conversion between
    domain models and OpenAI API data structures.
    """

    def __init__(self, client: Optional[OpenAIClient] = None) -> None:
        """Initialize the OpenAI adapter.

        Args:
            client: Optional existing OpenAIClient instance.
                   If not provided, a new one will be created.

        Raises:
            HTTPException: If connecting to OpenAI fails
        """
        try:
            self.client = client or OpenAIClient()
        except AuthenticationError as e:
            logger.error(f"OpenAI authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"OpenAI authentication error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize OpenAI client: {str(e)}",
            )

    async def check_health(self) -> Dict[str, Any]:
        """Check OpenAI API health.

        Returns:
            Dictionary containing health information
        """
        try:
            # Perform a simple embedding request to check if API is responsive
            model_name = self.client.embedding_model
            response_obj = await self.client._async_client.embeddings.create(
                deployment_name=model_name,
                model=model_name,
                input=["Health check"]
            )

            # Convert to our response model
            response = EmbeddingResponse.model_validate(response_obj.model_dump())

            if response and response.data and len(response.data) > 0:
                return {
                    "status": "healthy",
                    "details": {
                        "models": {
                            "embedding": self.client.embedding_model,
                            "chat": self.client.chat_model,
                            "reasoning": self.client.reasoning_model,
                        }
                    },
                }
            else:
                return {
                    "status": "degraded",
                    "details": {
                        "error": "OpenAI API returned invalid response",
                        "type": "OpenAIHealthCheckError",
                    },
                }

        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "details": {"error": str(e), "type": type(e).__name__},
            }

    async def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for the given texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            HTTPException: If embedding creation fails
        """
        try:
            # Call the OpenAI client directly using the async client
            model_name = self.client.embedding_model

            # Get the response directly from the async client
            response_obj = await self.client._async_client.embeddings.create(
                deployment_name=model_name,
                model=model_name,
                input=texts
            )

            # Convert to our response model
            response = EmbeddingResponse.model_validate(response_obj.model_dump())

            # Extract embeddings from the response
            embeddings = [item.embedding for item in response.data]
            return embeddings

        except InvalidRequestError as e:
            logger.error(f"Invalid request to OpenAI: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request to OpenAI: {str(e)}",
            )
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenAI API error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error creating embeddings: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )

    async def answer_question(
        self, request: AskRequest, context_items: List[Dict[str, Any]]
    ) -> AskAnswer:
        """Answer a natural language question using the code graph context.

        Args:
            request: The question and parameters
            context_items: Relevant context items from the graph

        Returns:
            AskAnswer with the generated response

        Raises:
            HTTPException: If answering the question fails
        """
        start_time = time.time()

        try:
            # Create references from context items
            references = []
            for item in context_items:
                ref_type = ReferenceType.FILE  # Default

                # Determine reference type from node labels
                if "labels" in item and isinstance(item["labels"], list):
                    labels = item["labels"]
                    if "Function" in labels:
                        ref_type = ReferenceType.FUNCTION
                    elif "Class" in labels:
                        ref_type = ReferenceType.CLASS
                    elif "Module" in labels:
                        ref_type = ReferenceType.MODULE
                    elif "Directory" in labels:
                        ref_type = ReferenceType.DIRECTORY
                    elif "Document" in labels:
                        ref_type = ReferenceType.DOCUMENT
                    elif "File" in labels:
                        ref_type = ReferenceType.FILE

                # Extract path if available
                path = None
                if "path" in item:
                    path = item["path"]
                elif "filePath" in item:
                    path = item["filePath"]

                # Extract snippet if available
                snippet = None
                for content_field in ["content", "body", "text", "code"]:
                    if content_field in item:
                        content = item[content_field]
                        if content and isinstance(content, str):
                            snippet = content
                            break

                # Add to references
                references.append(
                    Reference(
                        id=item.get("id", "unknown"),
                        type=ref_type,
                        name=item.get("name", "Unnamed"),
                        path=path,
                        snippet=snippet if request.include_code_snippets else None,
                        relevance_score=item.get("score", 0.5)
                        if "score" in item
                        else 0.5,
                    )
                )

            # Format context for the LLM
            context_text = "Context from the code repository:\n\n"
            for i, ref in enumerate(references):
                context_text += f"[{i+1}] {ref.type.value.capitalize()}: {ref.name}\n"
                if ref.path:
                    context_text += f"Path: {ref.path}\n"
                if ref.snippet and request.include_code_snippets:
                    context_text += f"Content:\n```\n{ref.snippet[:500]}{'...' if len(ref.snippet) > 500 else ''}\n```\n"
                context_text += "\n"

            # Create the prompt
            system_prompt = """You are a helpful assistant that answers questions about a code repository.
Answer the user's question based only on the provided context from the code repository.
If you cannot answer the question with the given context, say so clearly.
Be concise and accurate in your responses."""

            prompt = f"""
Question: {request.question}

{context_text}

Based on the above context, please answer the question. Reference the specific context items by their numbers where appropriate.
"""

            # Create the chat request
            chat_request = ChatCompletionRequest(
                model=self.client.chat_model,
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(role="user", content=prompt),
                ],
                temperature=0.2,  # Lower temperature for more factual responses
                max_tokens=1000,
            )

            # Call the OpenAI client
            response = await self.client.create_chat_completion_async(chat_request)

            # Generate conversation ID for continuity
            conversation_id = request.conversation_id or f"conv-{int(time.time())}"

            # Create the answer
            execution_time_ms = int((time.time() - start_time) * 1000)

            return AskAnswer(
                answer=response.choices[0].message.content,
                references=references,
                conversation_id=conversation_id,
                execution_time_ms=execution_time_ms,
                confidence_score=0.8,  # Default confidence, could be calculated based on context relevance
            )

        except InvalidRequestError as e:
            logger.error(f"Invalid request to OpenAI: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid request to OpenAI: {str(e)}",
            )
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenAI API error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error answering question: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )


async def get_openai_adapter() -> OpenAIAdapter:
    """Factory function to create an OpenAI adapter.

    This is used as a FastAPI dependency.

    Returns:
        OpenAIAdapter instance

    Raises:
        HTTPException: If connection to OpenAI fails
    """
    try:
        return OpenAIAdapter()
    except Exception as e:
        logger.error(f"Failed to create OpenAI adapter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create OpenAI adapter: {str(e)}",
        )
