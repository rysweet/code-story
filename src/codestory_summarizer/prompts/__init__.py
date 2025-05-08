"""Prompt templates for generating summaries of different node types.

This package provides specialized prompt templates for generating
high-quality summaries of different types of code elements.
"""

from typing import Dict, List, Optional, Union

from ..models import NodeData, NodeType

from .class_node import get_summary_prompt as get_class_summary_prompt
from .directory_node import get_summary_prompt as get_directory_summary_prompt
from .file_node import get_summary_prompt as get_file_summary_prompt
from .function_node import get_summary_prompt as get_function_summary_prompt
from .module_node import get_summary_prompt as get_module_summary_prompt


def get_summary_prompt(
    node: NodeData,
    content: str,
    context: List[str],
    child_summaries: Optional[List[str]] = None,
    max_tokens: int = 8000
) -> str:
    """Get an appropriate summary prompt for a node based on its type.
    
    Args:
        node: Node to generate prompt for
        content: Node content
        context: Contextual information about the node
        child_summaries: Summaries of child nodes (for higher-level nodes)
        max_tokens: Maximum tokens to include in the prompt
        
    Returns:
        Appropriate prompt for the node type
    """
    node_type = node.type
    
    if node_type == NodeType.FILE:
        return get_file_summary_prompt(
            content=content,
            context=context,
            file_path=node.path or "",
            max_tokens=max_tokens
        )
    elif node_type == NodeType.CLASS:
        return get_class_summary_prompt(
            content=content,
            context=context,
            max_tokens=max_tokens
        )
    elif node_type in (NodeType.FUNCTION, NodeType.METHOD):
        return get_function_summary_prompt(
            content=content,
            context=context,
            is_method=(node_type == NodeType.METHOD),
            max_tokens=max_tokens
        )
    elif node_type == NodeType.DIRECTORY:
        return get_directory_summary_prompt(
            content=content,
            context=context,
            child_summaries=child_summaries,
            max_tokens=max_tokens
        )
    elif node_type == NodeType.MODULE:
        return get_module_summary_prompt(
            content=content,
            context=context,
            child_summaries=child_summaries,
            max_tokens=max_tokens
        )
    elif node_type == NodeType.REPOSITORY:
        # For repository, use directory prompt but customize context
        if child_summaries is None:
            child_summaries = []
            
        context.insert(0, "Repository Root Directory")
            
        return get_directory_summary_prompt(
            content=content,
            context=context,
            child_summaries=child_summaries,
            max_tokens=max_tokens
        )
    else:
        # Generic prompt for other node types
        prompt = f"""You are an expert code summarizer. Analyze the following code and write a comprehensive summary.

Information:
{chr(10).join(context)}

Content:
```
{content}
```

Your task is to provide a concise, technical summary of what this code does, why it exists, and how it works.

Summary:
"""
        return prompt