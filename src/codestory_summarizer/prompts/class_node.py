"""Prompt templates for summarizing class nodes.

This module provides prompt templates specifically designed for generating
high-quality summaries of class nodes.
"""

from typing import Dict, List, Union


def get_class_summary_prompt(
    content: str, context: List[str], max_tokens: int = 8000
) -> str:
    """Generate a prompt for summarizing a class.

    Args:
        content: Class content
        context: Contextual information about the class
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a class summary
    """
    # Truncate content if it's too long
    if len(content) > max_tokens * 4:  # Rough estimate: 4 chars per token
        content = content[: max_tokens * 4] + "\n...[content truncated due to length]"

    prompt = f"""You are an expert code summarizer specializing in object-oriented design patterns. Analyze the following class and write a comprehensive summary.

Class information:
{chr(10).join(context)}

Class implementation:
```
{content}
```

Your task is to:
1. Summarize the main purpose and functionality of this class
2. Identify the key methods and properties and their significance
3. Explain how the class achieves encapsulation, inheritance, or polymorphism (if applicable)
4. Note any design patterns or programming paradigms being utilized
5. Describe the class's role in the broader application architecture

Your summary should be concise, technical, and informative. Focus on explaining WHAT the class does, WHY it exists, and HOW it accomplishes its purpose.

Summary:
"""

    return prompt


def get_summary_prompt(content: str, context: List[str], max_tokens: int = 8000) -> str:
    """Generate a prompt for summarizing a class.

    This is a wrapper around get_class_summary_prompt to maintain
    a consistent interface across prompt modules.

    Args:
        content: Class content
        context: Contextual information about the class
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a class summary
    """
    return get_class_summary_prompt(content, context, max_tokens)
