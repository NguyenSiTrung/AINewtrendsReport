"""Typer CLI entry point for ainews.

Usage::

    ainews --help          # show available commands
    ainews version         # print package version
    ainews llm --help      # LLM management commands (stub)
    ainews run --help      # pipeline execution commands (stub)
    ainews seed --help     # seed data commands (stub)
"""

from __future__ import annotations

import typer

from ainews import __version__

# ── Main app ──────────────────────────────────────────────
app = typer.Typer(
    name="ainews",
    help="AI News & Trends Report — automated intelligence pipeline.",
    no_args_is_help=True,
)

# ── Stub sub-apps ─────────────────────────────────────────
llm_app = typer.Typer(help="LLM server management commands.")
run_app = typer.Typer(help="Pipeline execution commands.")
seed_app = typer.Typer(help="Seed data management commands.")

app.add_typer(llm_app, name="llm")
app.add_typer(run_app, name="run")
app.add_typer(seed_app, name="seed")


# ── Commands ──────────────────────────────────────────────
@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(f"ainews {__version__}")
