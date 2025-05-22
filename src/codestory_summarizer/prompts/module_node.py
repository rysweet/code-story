"""Prompt templates for summarizing module nodes.

This module provides prompt templates specifically designed for generating
high-quality summaries of module nodes.
"""



def get_module_summary_prompt(
    content: str,
    context: list[str],
    child_summaries: list[str] = [],  # Use empty list instead of None
    max_tokens: int = 8000,
) -> str:
    """Generate a prompt for summarizing a module.

    Args:
        content: Module content
        context: Contextual information about the module
        child_summaries: Summaries of child nodes
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a module summary
    """
    # Truncate content if it's too long
    if len(content) > max_tokens * 4:  # Rough estimate: 4 chars per token
        content = content[: max_tokens * 4] + "\n...[content truncated due to length]"

    prompt = f"""You are an expert code architect. Analyze the following module and write a comprehensive summary.

Module information:
{chr(10).join(context)}

"""

    if child_summaries:
        prompt += f"""Summaries of contained components:
{chr(10).join(child_summaries)}

"""

    prompt += f"""Module content:
```
{content}
```

Your task is to:
1. Summarize the overall purpose and functionality of this module
2. Identify the key exported functions, classes, or variables
3. Explain the module's interface and how other code would use it
4. Describe any important patterns or design principles implemented
5. Note the module's role in the larger codebase architecture

Your summary should be concise, technical, and informative. Focus on explaining WHAT the module does, WHY it exists, and HOW it should be used.

Summary:
"""

    return prompt


def get_summary_prompt(
    content: str,
    context: list[str],
    child_summaries: list[str] = [],  # Use empty list instead of None
    max_tokens: int = 8000,
) -> str:
    """Generate a prompt for summarizing a module.

    This is a wrapper around get_module_summary_prompt to maintain
    a consistent interface across prompt modules.

    Args:
        content: Module content
        context: Contextual information about the module
        child_summaries: Summaries of child nodes
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a module summary
    """
    # Use child_summaries directly since empty list is already the default
    return get_module_summary_prompt(content, context, child_summaries, max_tokens)
