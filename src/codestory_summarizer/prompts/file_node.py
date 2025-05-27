"""Prompt templates for summarizing file nodes.

This module provides prompt templates specifically designed for generating
high-quality summaries of file nodes.
"""


def get_file_summary_prompt(
    content: str, context: list[str], max_tokens: int = 8000
) -> str:
    """Generate a prompt for summarizing a file.

    Args:
        content: File content
        context: Contextual information about the file
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a file summary
    """
    # Truncate content if it's too long
    if len(content) > max_tokens * 4:  # Rough estimate: 4 chars per token
        content = content[: max_tokens * 4] + "\n...[content truncated due to length]"

    prompt = f"""You are an expert code summarizer. Analyze the following file and write a comprehensive summary.

File information:
{chr(10).join(context)}

File content:
```
{content}
```

Your task is to:
1. Summarize the main purpose and functionality of this file
2. Identify key components, classes, or functions 
3. Describe the file's role in the broader codebase (based on imports and dependencies)
4. Note any important patterns, algorithms, or techniques used
5. Mention the tech stack or frameworks being utilized

Your summary should be concise, technical, and informative. Aim for 3-5 paragraphs (depending on complexity). Focus on explaining WHAT the code does, WHY it exists, and HOW it accomplishes its purpose.

Summary:
"""

    return prompt


def get_config_file_summary_prompt(
    content: str, context: list[str], max_tokens: int = 8000
) -> str:
    """Generate a prompt for summarizing a configuration file.

    Args:
        content: File content
        context: Contextual information about the file
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Prompt for generating a configuration file summary
    """
    # Truncate content if it's too long
    if len(content) > max_tokens * 4:
        content = content[: max_tokens * 4] + "\n...[content truncated due to length]"

    prompt = f"""You are an expert at analyzing configuration files. Analyze the following configuration file and write a comprehensive summary.

File information:
{chr(10).join(context)}

File content:
```
{content}
```

Your task is to:
1. Summarize the purpose of this configuration file
2. Identify the key settings and their significance
3. Explain how this configuration affects the system or application
4. Note any environment-specific settings or variables
5. Identify any security-relevant configurations

Your summary should be concise, technical, and informative. Focus on explaining WHAT is being configured, WHY these settings matter, and HOW they impact the system.

Summary:
"""

    return prompt


def is_config_file(file_path: str, content: str) -> bool:
    """Determine if a file is a configuration file.

    Args:
        file_path: Path to the file
        content: File content

    Returns:
        True if the file is a configuration file, False otherwise
    """
    # Check file extension
    config_extensions = {
        "json",
        "yaml",
        "yml",
        "toml",
        "ini",
        "conf",
        "config",
        "properties",
        "env",
        "cfg",
        "rc",
        "xml",
    }

    # Check filename patterns
    config_patterns = {
        "config",
        "configuration",
        "settings",
        "setup",
        "options",
        ".env",
        "dockerfile",
        "docker-compose",
        "package.json",
        "tsconfig",
        "webpack",
        "babel",
        "jest",
        "eslint",
        "prettier",
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "pom.xml",
        "gradle",
        "makefile",
        "cmake",
    }

    # Extract file extension
    if "." in file_path:
        ext = file_path.split(".")[-1].lower()
        if ext in config_extensions:
            return True

    # Check filename
    filename = file_path.lower().split("/")[-1]

    return any(pattern in filename for pattern in config_patterns)


def get_summary_prompt(
    content: str, context: list[str], file_path: str = "", max_tokens: int = 8000
) -> str:
    """Generate an appropriate prompt based on the file type.

    Args:
        content: File content
        context: Contextual information about the file
        file_path: Path to the file
        max_tokens: Maximum tokens to include in the prompt

    Returns:
        Appropriate prompt for the file type
    """
    if is_config_file(file_path, content):
        return get_config_file_summary_prompt(content, context, max_tokens)
    else:
        return get_file_summary_prompt(content, context, max_tokens)
