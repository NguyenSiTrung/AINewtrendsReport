"""Typer CLI entry point for ainews.

Usage::

    ainews --help          # show available commands
    ainews version         # print package version
    ainews seed            # populate database with starter sites and schedules
    ainews llm test        # test LLM server connectivity
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

# ── Sub-apps ──────────────────────────────────────────────
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


@llm_app.command(name="test")
def llm_test() -> None:
    """Test LLM server connectivity.

    Resolves config from env/settings, displays it (with masked API key),
    issues a 1-token completion, and prints the result.
    """
    from ainews.core.config import Settings
    from ainews.llm.connectivity import check_llm_connection
    from ainews.llm.factory import get_llm_config

    settings = Settings()
    config = get_llm_config(settings)

    typer.echo("── Resolved LLM Config ──")
    typer.echo(f"  base_url:    {config.base_url}")
    typer.echo(f"  api_key:     {config.masked_api_key}")
    typer.echo(f"  model:       {config.model}")
    typer.echo(f"  temperature: {config.temperature}")
    typer.echo(f"  max_tokens:  {config.max_tokens}")
    typer.echo(f"  timeout:     {config.timeout}s")
    typer.echo("")
    typer.echo("Testing connection…")

    result = check_llm_connection(config)

    if result.success:
        typer.echo(typer.style("✓ Connection OK", fg=typer.colors.GREEN))
        typer.echo(f"  model:   {result.model_name}")
        typer.echo(f"  latency: {result.latency_ms:.1f}ms")
    else:
        typer.echo(typer.style("✗ Connection FAILED", fg=typer.colors.RED))
        typer.echo(f"  error: {result.error}")
        raise typer.Exit(code=1)


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
