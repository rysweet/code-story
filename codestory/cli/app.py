import typer

app = typer.Typer(help="CodeStory command-line interface")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Root entrypoint – shows help if no sub-command given.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
