from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure the src/ package root is importable when running via the alembic CLI
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from alembic import context  # noqa: E402

# Side-effect import: registers all 8 models with Base.metadata
import ainews.models  # noqa: E402, F401

from ainews.core.config import Settings  # noqa: E402
from ainews.core.database import create_engine as _create_engine  # noqa: E402
from ainews.models.base import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_url() -> str:
    """Resolve the database URL from alembic.ini or application Settings."""
    url = config.get_main_option("sqlalchemy.url", "")
    if url and not url.startswith("sqlite+pysqlite:///./var"):
        return url
    return Settings().database_url


def run_migrations_offline() -> None:
    """Run migrations in offline mode (generates SQL without a live DB)."""
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    engine = _create_engine(_get_url())
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
