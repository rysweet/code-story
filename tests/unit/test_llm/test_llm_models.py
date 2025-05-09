"""Tests for OpenAI client models."""


from codestory.llm.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatFunctionCall,
    ChatMessage,
    ChatResponseChoice,
    ChatResponseMessage,
    ChatRole,
    CompletionChoice,
    CompletionRequest,
    CompletionResponse,
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    UsageInfo,
)


def test_llm_chat_role_enum():
    """Test ChatRole enum values."""
    assert ChatRole.SYSTEM == "system"
    assert ChatRole.USER == "user"
    assert ChatRole.ASSISTANT == "assistant"
    assert ChatRole.FUNCTION == "function"
    assert ChatRole.TOOL == "tool"


def test_llm_chat_message():
    """Test ChatMessage model."""
    # Basic message
    message = ChatMessage(role=ChatRole.USER, content="Hello")
    assert message.role == ChatRole.USER
    assert message.content == "Hello"
    assert message.name is None
    
    # With name
    message = ChatMessage(role=ChatRole.FUNCTION, content="Result", name="get_weather")
    assert message.role == ChatRole.FUNCTION
    assert message.content == "Result"
    assert message.name == "get_weather"
    
    # From dict
    message_dict = {
        "role": "system",
        "content": "You are a helpful assistant."
    }
    message = ChatMessage(**message_dict)
    assert message.role == ChatRole.SYSTEM
    assert message.content == "You are a helpful assistant."


def test_llm_chat_function_call():
    """Test ChatFunctionCall model."""
    func_call = ChatFunctionCall(
        name="get_weather",
        arguments='{"location": "New York", "unit": "celsius"}'
    )
    assert func_call.name == "get_weather"
    assert func_call.arguments == '{"location": "New York", "unit": "celsius"}'


def test_llm_chat_response_message():
    """Test ChatResponseMessage model."""
    # Simple message
    message = ChatResponseMessage(role=ChatRole.ASSISTANT, content="Hello there!")
    assert message.role == ChatRole.ASSISTANT
    assert message.content == "Hello there!"
    assert message.function_call is None
    
    # With function call
    func_call = ChatFunctionCall(
        name="get_weather",
        arguments='{"location": "New York"}'
    )
    message = ChatResponseMessage(
        role=ChatRole.ASSISTANT,
        content=None,
        function_call=func_call
    )
    assert message.role == ChatRole.ASSISTANT
    assert message.content is None
    assert message.function_call.name == "get_weather"


def test_llm_chat_response_choice():
    """Test ChatResponseChoice model."""
    message = ChatResponseMessage(role=ChatRole.ASSISTANT, content="Hello there!")
    choice = ChatResponseChoice(
        index=0,
        message=message,
        finish_reason="stop"
    )
    assert choice.index == 0
    assert choice.message.content == "Hello there!"
    assert choice.finish_reason == "stop"


def test_llm_completion_choice():
    """Test CompletionChoice model."""
    choice = CompletionChoice(
        text="Paris is the capital of France.",
        index=0,
        finish_reason="stop"
    )
    assert choice.text == "Paris is the capital of France."
    assert choice.index == 0
    assert choice.finish_reason == "stop"
    assert choice.logprobs is None


def test_llm_embedding_data():
    """Test EmbeddingData model."""
    data = EmbeddingData(
        embedding=[0.1, 0.2, 0.3, 0.4],
        index=0
    )
    assert data.embedding == [0.1, 0.2, 0.3, 0.4]
    assert data.index == 0
    assert data.object == "embedding"


def test_llm_usage_info():
    """Test UsageInfo model."""
    usage = UsageInfo(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150
    )
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150


def test_llm_completion_request():
    """Test CompletionRequest model."""
    # Basic request
    request = CompletionRequest(
        model="text-davinci-003",
        prompt="Write a poem about AI."
    )
    assert request.model == "text-davinci-003"
    assert request.prompt == "Write a poem about AI."
    assert request.max_tokens is None
    
    # Full request
    request = CompletionRequest(
        model="text-davinci-003",
        prompt="Write a poem about AI.",
        max_tokens=100,
        temperature=0.7,
        top_p=0.9,
        n=1,
        stop=["\n\n"],
        presence_penalty=0.0,
        frequency_penalty=0.0
    )
    assert request.model == "text-davinci-003"
    assert request.max_tokens == 100
    assert request.temperature == 0.7
    assert request.stop == ["\n\n"]


def test_llm_chat_completion_request():
    """Test ChatCompletionRequest model."""
    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are a helpful assistant."),
        ChatMessage(role=ChatRole.USER, content="Hello, assistant!")
    ]
    
    # Basic request
    request = ChatCompletionRequest(
        model="gpt-4",
        messages=messages
    )
    assert request.model == "gpt-4"
    assert len(request.messages) == 2
    assert request.messages[0].role == ChatRole.SYSTEM
    assert request.messages[1].content == "Hello, assistant!"
    
    # Full request
    request = ChatCompletionRequest(
        model="gpt-4",
        messages=messages,
        max_tokens=100,
        temperature=0.8,
        presence_penalty=0.1,
        frequency_penalty=0.1,
        response_format={"type": "json_object"}
    )
    assert request.max_tokens == 100
    assert request.temperature == 0.8
    assert request.response_format == {"type": "json_object"}


def test_llm_embedding_request():
    """Test EmbeddingRequest model."""
    # String input
    request = EmbeddingRequest(
        model="text-embedding-3-small",
        input="Hello world"
    )
    assert request.model == "text-embedding-3-small"
    assert request.input == "Hello world"
    
    # List input
    request = EmbeddingRequest(
        model="text-embedding-3-small",
        input=["Hello world", "How are you?"]
    )
    assert request.model == "text-embedding-3-small"
    assert request.input == ["Hello world", "How are you?"]
    assert len(request.input) == 2
    
    # With dimensions
    request = EmbeddingRequest(
        model="text-embedding-3-small",
        input="Hello world",
        dimensions=256
    )
    assert request.dimensions == 256


def test_llm_completion_response():
    """Test CompletionResponse model."""
    choice = CompletionChoice(
        text="Paris is the capital of France.",
        index=0,
        finish_reason="stop"
    )
    usage = UsageInfo(
        prompt_tokens=10,
        completion_tokens=8,
        total_tokens=18
    )
    
    response = CompletionResponse(
        id="cmpl-123",
        object="text_completion",
        created=1677858242,
        model="text-davinci-003",
        choices=[choice],
        usage=usage
    )
    
    assert response.id == "cmpl-123"
    assert response.model == "text-davinci-003"
    assert len(response.choices) == 1
    assert response.choices[0].text == "Paris is the capital of France."
    assert response.usage.total_tokens == 18


def test_llm_chat_completion_response():
    """Test ChatCompletionResponse model."""
    message = ChatResponseMessage(role=ChatRole.ASSISTANT, content="Hello there!")
    choice = ChatResponseChoice(
        index=0,
        message=message,
        finish_reason="stop"
    )
    usage = UsageInfo(
        prompt_tokens=15,
        completion_tokens=3,
        total_tokens=18
    )
    
    response = ChatCompletionResponse(
        id="chatcmpl-123",
        object="chat.completion",
        created=1677858242,
        model="gpt-4",
        choices=[choice],
        usage=usage
    )
    
    assert response.id == "chatcmpl-123"
    assert response.model == "gpt-4"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hello there!"
    assert response.usage.prompt_tokens == 15


def test_llm_embedding_response():
    """Test EmbeddingResponse model."""
    data1 = EmbeddingData(
        embedding=[0.1, 0.2, 0.3, 0.4],
        index=0
    )
    data2 = EmbeddingData(
        embedding=[0.5, 0.6, 0.7, 0.8],
        index=1
    )
    usage = UsageInfo(
        prompt_tokens=8,
        total_tokens=8
    )
    
    response = EmbeddingResponse(
        object="list",
        data=[data1, data2],
        model="text-embedding-3-small",
        usage=usage
    )
    
    assert response.object == "list"
    assert response.model == "text-embedding-3-small"
    assert len(response.data) == 2
    assert response.data[0].embedding == [0.1, 0.2, 0.3, 0.4]
    assert response.data[1].embedding == [0.5, 0.6, 0.7, 0.8]
    assert response.usage.prompt_tokens == 8