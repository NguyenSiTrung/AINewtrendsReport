# SQL & Database Style Guide

## SQLAlchemy Models

### Model Definition

```python
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, default="news")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[str] = mapped_column(String)  # ISO8601
```

### Conventions

- **Use `Mapped[]` + `mapped_column()`** (SQLAlchemy 2.0 style, not legacy `Column()`)
- **Table names:** plural snake_case (`sites`, `articles`, `run_logs`)
- **Model names:** singular PascalCase (`Site`, `Article`, `RunLog`)
- **Primary keys:** `id: Mapped[int]` (auto-increment) or `id: Mapped[str]` (UUID text)
- **Timestamps:** Store as ISO8601 text strings (SQLite has no native datetime)
- **JSON columns:** Use `JSON` type (SQLite JSON1 extension)
- **Boolean columns:** Use `Integer` (0/1) — SQLite has no native boolean
- **Foreign keys:** Always define with `ForeignKey("table.column")`

### Relationships

- Define on the "parent" side with `back_populates`
- Use `lazy="selectin"` for small related sets; avoid `lazy="joined"` for large collections

## Alembic Migrations

- **One migration per logical change** — don't combine unrelated schema changes
- **Descriptive revision messages:** `"add_sites_table"`, `"add_fts5_reports_search"`
- **Always include `downgrade()`** — even if it's a `drop_table`
- **Test migrations:** `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head`

## SQLite-Specific Rules

### Connection Pragmas (applied at connection time)

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=268435456")
    cursor.close()
```

### Query Patterns

- **Use parameterized queries** — never string-interpolate SQL values
- **Batch inserts:** Use `session.add_all()` for bulk operations
- **FTS5 queries:** Use `MATCH` syntax, not `LIKE`
- **Avoid `SELECT *`** — explicitly list columns in raw SQL

### Concurrency

- SQLite allows **one writer** at a time (WAL mode enables concurrent readers)
- Keep write transactions short; commit frequently
- Use `busy_timeout` to handle lock contention gracefully
