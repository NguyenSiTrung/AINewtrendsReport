"""Typer CLI entry point for ainews.

Usage::

    ainews --help          # show available commands
    ainews version         # print package version
    ainews seed            # populate database with starter sites and schedules
    ainews llm --help      # LLM management commands (stub)
    ainews run --help      # pipeline execution commands (stub)
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
seed_app = typer.Typer(
    help="Seed the database with starter sites and schedules.",
    invoke_without_command=True,
)

app.add_typer(llm_app, name="llm")
app.add_typer(run_app, name="run")
app.add_typer(seed_app, name="seed")


# ── Commands ──────────────────────────────────────────────
@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(f"ainews {__version__}")


@seed_app.callback(invoke_without_command=True)
def seed(ctx: typer.Context) -> None:
    """Populate the database with 10 starter sites and 1 weekly schedule."""
    if ctx.invoked_subcommand is not None:
        return

    from ainews.core.config import Settings
    from ainews.core.database import create_engine, get_db_session
    from ainews.seed import seed_all

    settings = Settings()
    engine = create_engine(settings.database_url)
    with get_db_session(engine) as session:
        result = seed_all(session)
    engine.dispose()

    typer.echo(f"Sites: {result.sites_created} created, {result.sites_skipped} skipped")
    typer.echo(
        f"Schedules: {result.schedules_created} created,"
        f" {result.schedules_skipped} skipped"
    )
