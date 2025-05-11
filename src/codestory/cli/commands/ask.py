"""
Natural language query commands for the Code Story CLI.
"""

import json
from typing import Dict, Any, Optional

import click
# Import rich_click if available, otherwise create a stub
try:
    import rich_click
except ImportError:
    import click as rich_click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..client import ServiceClient, ServiceError


@click.command(help="Ask a natural language question about the codebase.")
@click.argument("question")
@click.option("--json", "output_json", is_flag=True, help="Output raw JSON.")
@click.pass_context
def ask(ctx: click.Context, question: str, output_json: bool = False) -> None:
    """
    Ask a natural language question about the codebase.
    
    QUESTION is the natural language question to ask.
    """
    client: ServiceClient = ctx.obj["client"]
    console: Console = ctx.obj["console"]
    
    console.print(f"Asking: [cyan]{question}[/]")
    
    try:
        result = client.ask_question(question)
        
        if output_json:
            # Output raw JSON
            console.print(json.dumps(result, indent=2))
            return
        
        # Output formatted answer
        answer = result.get("answer", "No answer found.")
        sources = result.get("sources", [])
        
        # Display answer with Markdown formatting
        console.print(Panel(
            Markdown(answer),
            title="Answer",
            border_style="green"
        ))
        
        # Display sources if available
        if sources:
            console.print("\n[bold]Sources:[/]")
            
            for i, source in enumerate(sources, 1):
                source_type = source.get("type", "unknown")
                source_id = source.get("id", "")
                source_name = source.get("name", source_id)
                source_path = source.get("path", "")
                source_score = source.get("score", 0)
                
                console.print(
                    f"{i}. [cyan]{source_name}[/] "
                    f"([blue]{source_type}[/]) "
                    f"[dim]{source_path}[/] "
                    f"- Score: [yellow]{source_score:.2f}[/]"
                )
    
    except ServiceError as e:
        console.print(f"[bold red]Query failed:[/] {str(e)}")