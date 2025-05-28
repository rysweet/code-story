"""Prompt templates for summarizing directory nodes.

This module provides prompt templates specifically designed for generating
high-quality summaries of directory nodes.
"""


def get_directory_summary_prompt(
    content: str,
    context: list[str],
    child_summaries: list[str] | None = None,  # Use empty list instead of None
    max_tokens: int = 8000,
) -> str:
    """Generate a prompt for summarizing a directory.

    Args:
        content: Directory content description
        context: Contextual information about the directory
        child_summaries: Summaries of child nodes
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a directory summary
    """
    if child_summaries is None:
        child_summaries = []
    prompt = f"""You are an expert software architect. Analyze the following directory and write a 
comprehensive summary.

Directory information:
{chr(10).join(context)}

"""

    if child_summaries:
        prompt += f"""Summaries of contained files and subdirectories:
{chr(10).join(child_summaries)}

"""

    prompt += """Your task is to:
1. Summarize the overall purpose and functionality of this directory
2. Identify the key components and their relationships
3. Explain the architectural patterns or design principles evident in this directory
4. Describe how this directory fits into the larger project structure
5. Note any important conventions, patterns, or organization strategies

Your summary should be concise, technical, and informative. Focus on explaining WHAT the directory 
contains, WHY it exists, and HOW it contributes to the overall project architecture.

Summary:
"""

    return prompt


def get_summary_prompt(
    content: str,
    context: list[str],
    child_summaries: list[str] | None = None,  # Use empty list instead of None
    max_tokens: int = 8000,
) -> str:
    """Generate a prompt for summarizing a directory.

    This is a wrapper around get_directory_summary_prompt to maintain
    a consistent interface across prompt modules.

    Args:
        content: Directory content description
        context: Contextual information about the directory
        child_summaries: Summaries of child nodes
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a directory summary
    """
    if child_summaries is None:
        child_summaries = []
    return get_directory_summary_prompt(content, context, child_summaries, max_tokens)
