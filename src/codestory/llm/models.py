"""Data models for OpenAI API requests and responses.

This module defines Pydantic models for serializing and deserializing
requests and responses for the Azure OpenAI API.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, TypeVar
from pydantic import BaseModel, Field, ConfigDict


class ChatRole(str, Enum):
    """Roles for chat messages."""
    
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A message in a chat conversation."""
    
    role: ChatRole
    content: str
    name: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")


class ChatFunctionCall(BaseModel):
    """A function call in a chat response."""
    
    name: str
    arguments: str
    
    model_config = ConfigDict(extra="allow")


class ChatResponseMessage(BaseModel):
    """A message in a chat completion response."""
    
    role: ChatRole
    content: Optional[str] = None
    function_call: Optional[ChatFunctionCall] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    
    model_config = ConfigDict(extra="allow")


class ChatResponseChoice(BaseModel):
    """A choice in a chat completion response."""

    index: int
    message: ChatResponseMessage
    finish_reason: Optional[str] = None

    model_config = ConfigDict(extra="allow")


# Aliases for backward compatibility
ChatCompletionResponseChoice = ChatResponseChoice


class CompletionChoice(BaseModel):
    """A choice in a completion response."""
    
    text: str
    index: int
    finish_reason: Optional[str] = None
    logprobs: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(extra="allow")


class EmbeddingData(BaseModel):
    """Embedding data for a single input."""
    
    embedding: List[float]
    index: int
    object: str = "embedding"
    
    model_config = ConfigDict(extra="allow")


class UsageInfo(BaseModel):
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: Optional[int] = None
    total_tokens: int

    model_config = ConfigDict(extra="allow")


# Aliases for backward compatibility
Usage = UsageInfo


# Request Models

class CompletionRequest(BaseModel):
    """Parameters for a completion request."""
    
    model: str
    prompt: Union[str, List[str], List[int], List[List[int]]]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    logprobs: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    best_of: Optional[int] = None
    user: Optional[str] = None
    
    model_config = ConfigDict(extra="allow")


class ChatCompletionRequest(BaseModel):
    """Parameters for a chat completion request."""
    
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Union[str, Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None
    
    model_config = ConfigDict(extra="allow")


class EmbeddingRequest(BaseModel):
    """Parameters for an embedding request."""
    
    model: str
    input: Union[str, List[str], List[int], List[List[int]]]
    user: Optional[str] = None
    dimensions: Optional[int] = None
    
    model_config = ConfigDict(extra="allow")


# Response Models

class CompletionResponse(BaseModel):
    """Response from a completion request."""
    
    id: str
    object: str
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: Optional[UsageInfo] = None
    
    model_config = ConfigDict(extra="allow")


class ChatCompletionResponse(BaseModel):
    """Response from a chat completion request."""
    
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatResponseChoice]
    usage: Optional[UsageInfo] = None
    
    model_config = ConfigDict(extra="allow")


class EmbeddingResponse(BaseModel):
    """Response from an embedding request."""
    
    object: str
    data: List[EmbeddingData]
    model: str
    usage: UsageInfo
    
    model_config = ConfigDict(extra="allow")