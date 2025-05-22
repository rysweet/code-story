"""Prompt templates for summarizing function and method nodes.

This module provides prompt templates specifically designed for generating
high-quality summaries of function and method nodes.
"""


def get_function_summary_prompt(
    content: str, context: list[str], max_tokens: int = 8000
) -> str:
    """Generate a prompt for summarizing a function.

    Args:
        content: Function content
        context: Contextual information about the function
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a function summary
    """
    # Truncate content if it's too long
    if len(content) > max_tokens * 4:  # Rough estimate: 4 chars per token
        content = content[: max_tokens * 4] + "\n...[content truncated due to length]"

    prompt = f"""You are an expert code summarizer specializing in function analysis. Analyze the following function and write a comprehensive summary.

Function information:
{chr(10).join(context)}

Function implementation:
```
{content}
```

Your task is to:
1. Summarize the main purpose and functionality of this function
2. Identify the input parameters and return values
3. Explain the algorithm or process implemented by the function
4. Note any edge cases or error handling mechanisms
5. Describe any key optimizations or techniques used

Your summary should be concise, technical, and informative. Focus on explaining WHAT the function does, WHY it exists, and HOW it accomplishes its purpose.

Summary:
"""

    return prompt


def get_method_summary_prompt(
    content: str, context: list[str], max_tokens: int = 8000
) -> str:
    """Generate a prompt for summarizing a method.

    Args:
        content: Method content
        context: Contextual information about the method
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a method summary
    """
    # Truncate content if it's too long
    if len(content) > max_tokens * 4:  # Rough estimate: 4 chars per token
        content = content[: max_tokens * 4] + "\n...[content truncated due to length]"

    prompt = f"""You are an expert code summarizer specializing in object-oriented design. Analyze the following method and write a comprehensive summary.

Method information:
{chr(10).join(context)}

Method implementation:
```
{content}
```

Your task is to:
1. Summarize the main purpose and functionality of this method
2. Identify the input parameters and return values
3. Explain how this method contributes to the overall class behavior
4. Note any overriding of parent class methods or implementation of interface methods
5. Describe any side effects or state changes this method causes

Your summary should be concise, technical, and informative. Focus on explaining WHAT the method does, WHY it exists, and HOW it accomplishes its purpose within the class.

Summary:
"""

    return prompt


def get_summary_prompt(
    content: str, context: list[str], is_method: bool = False, max_tokens: int = 8000
) -> str:
    """Generate an appropriate prompt based on whether it's a function or method.

    Args:
        content: Function/method content
        context: Contextual information about the function/method
        is_method: Whether this is a method (as opposed to a function)
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Appropriate prompt for the function/method
    """
    if is_method:
        return get_method_summary_prompt(content, context, max_tokens)
    else:
        return get_function_summary_prompt(content, context, max_tokens)
