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


# ── Run commands ──────────────────────────────────────────
@run_app.command(name="start")
def run_start(
    topic: list[str] = typer.Option(
        ...,
        "--topic",
        "-t",
        help="Topics to search (can specify multiple).",
    ),
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        help="Timeframe window in days.",
    ),
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Max articles to process.",
    ),
    site: list[str] | None = typer.Option(
        None,
        "--site",
        "-s",
        help="Restrict search to specific sites.",
    ),
    output_dir: str = typer.Option(
        "var/reports",
        "--output",
        "-o",
        help="Output directory for reports.",
    ),
) -> None:
    """Execute the LangGraph pipeline and generate a report.

    Example::

        ainews run start --topic "AI" --topic "LLM" --days 7
    """
    import uuid
    from pathlib import Path

    from langgraph.checkpoint.sqlite import SqliteSaver

    from ainews.agents.graph import build_graph
    from ainews.agents.state import GraphState, RunParams

    run_id = str(uuid.uuid4())[:8]
    params = RunParams(
        timeframe_days=days,
        topics=list(topic),
        sites=list(site) if site else [],
    )

    typer.echo(f"🚀 Starting pipeline run: {run_id}")
    typer.echo(f"   Topics: {', '.join(topic)} | Window: {days}d | Limit: {limit}")

    initial_state: GraphState = {
        "run_id": run_id,
        "params": params,
        "queries": [],
        "raw_results": [],
        "fetched_articles": [],
        "filtered_articles": [],
        "clusters": [],
        "summaries": [],
        "trends": [],
        "report_md": "",
        "xlsx_path": "",
        "errors": [],
        "metrics": {},
        "loop_count": 0,
    }

    # Run with checkpointing
    checkpoint_dir = Path(output_dir) / run_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_db = str(checkpoint_dir / "checkpoint.db")

    try:
        with SqliteSaver.from_conn_string(checkpoint_db) as cp:
            graph = build_graph(checkpointer=cp)
            config = {"configurable": {"thread_id": run_id}}
            result = graph.invoke(initial_state, config)

        # Persist report
        report_path = checkpoint_dir / "report.md"
        report_path.write_text(result.get("report_md", ""))

        typer.echo("")
        typer.echo(typer.style("✓ Report generated", fg=typer.colors.GREEN))
        typer.echo(f"  Path: {report_path}")
        typer.echo(
            f"  Queries: {len(result.get('queries', []))} | "
            f"Summaries: {len(result.get('summaries', []))} | "
            f"Trends: {len(result.get('trends', []))}"
        )

        errors = result.get("errors", [])
        if errors:
            typer.echo(
                typer.style(
                    f"  ⚠ {len(errors)} errors during execution",
                    fg=typer.colors.YELLOW,
                )
            )

    except Exception as exc:
        typer.echo(typer.style(f"✗ Pipeline failed: {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from exc


@app.command(name="trigger-run")
def trigger_run(
    schedule: str | None = typer.Option(
        None,
        "--schedule",
        "-s",
        help="Named schedule to execute.",
    ),
    topics: str | None = typer.Option(
        None,
        "--topics",
        help='Comma-separated topics for a one-off run (e.g. "AI,ML").',
    ),
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        help="Timeframe window in days.",
    ),
) -> None:
    """Enqueue a pipeline run via the shared service layer.

    Uses the same code path as ``POST /api/trigger`` — creates a Run row
    and enqueues a Celery task for background execution.

    Examples::

        ainews trigger-run --schedule weekly-ai-news
        ainews trigger-run --topics "AI,ML" --days 7
    """
    from ainews.core.config import Settings
    from ainews.core.database import create_engine, get_db_session
    from ainews.services.pipeline import create_and_enqueue_run

    params: dict[str, object] = {}
    if topics:
        params["topics"] = [t.strip() for t in topics.split(",")]
    if days:
        params["timeframe_days"] = days

    settings = Settings()
    engine = create_engine(settings.database_url)

    try:
        with get_db_session(engine) as session:
            run_id = create_and_enqueue_run(
                session,
                schedule_name=schedule,
                params=params or None,
                triggered_by="cli",
            )
    except ValueError as exc:
        typer.echo(typer.style(f"✗ {exc}", fg=typer.colors.RED))
        raise typer.Exit(code=1) from exc
    finally:
        engine.dispose()

    typer.echo(f"✓ Run enqueued: {run_id}")
    typer.echo(f"  triggered_by: cli")
    if schedule:
        typer.echo(f"  schedule: {schedule}")
    typer.echo("  Monitor via: GET /api/runs/" + run_id)


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
