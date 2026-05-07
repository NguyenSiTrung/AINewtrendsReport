"""Typer CLI entry point — stub for initial setup."""

import typer

app = typer.Typer(name="ainews", help="AI News & Trends Report CLI")


@app.command()
def version() -> None:
    """Print the package version."""
    from ainews import __version__

    typer.echo(f"ainews {__version__}")
