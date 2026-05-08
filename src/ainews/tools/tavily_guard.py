"""Tavily monthly-quota guard.

Tracks API call count per month in ``settings_kv`` and enforces a
configurable monthly cap. Auto-resets on new month.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from ainews.models.settings_kv import SettingsKV

logger = structlog.get_logger(__name__)

_DEFAULT_MONTHLY_CAP = 1000
_CAP_SETTING_KEY = "tavily_monthly_cap"


def _month_key() -> str:
    """Return the settings_kv key for the current month's counter."""
    now = datetime.now(tz=timezone.utc)
    return f"tavily_calls_{now.strftime('%Y_%m')}"


def get_monthly_cap(session: Session) -> int:
    """Read the monthly cap from settings_kv, or return default."""
    row = session.execute(
        select(SettingsKV).filter_by(key=_CAP_SETTING_KEY)
    ).scalar_one_or_none()
    if row is not None and isinstance(row.value, int):
        return row.value
    return _DEFAULT_MONTHLY_CAP


def get_current_count(session: Session) -> int:
    """Get the current month's API call count."""
    key = _month_key()
    row = session.execute(
        select(SettingsKV).filter_by(key=key)
    ).scalar_one_or_none()
    if row is not None and isinstance(row.value, int):
        return row.value
    return 0


def increment_count(session: Session) -> int:
    """Increment the current month's API call count. Returns new count."""
    key = _month_key()
    now_str = datetime.now(tz=timezone.utc).isoformat()

    row = session.execute(
        select(SettingsKV).filter_by(key=key)
    ).scalar_one_or_none()

    if row is not None:
        new_count = (row.value if isinstance(row.value, int) else 0) + 1
        row.value = new_count
        row.updated_at = now_str
    else:
        new_count = 1
        session.add(SettingsKV(key=key, value=new_count, updated_at=now_str))

    session.flush()
    return new_count


def is_quota_available(session: Session) -> bool:
    """Check if the Tavily quota is still available for this month.

    Returns ``True`` if under the cap, ``False`` if cap reached.
    """
    current = get_current_count(session)
    cap = get_monthly_cap(session)
    available = current < cap

    if not available:
        logger.warning(
            "tavily_quota_exceeded",
            current_count=current,
            monthly_cap=cap,
            month_key=_month_key(),
        )

    return available


def check_and_increment(session: Session) -> bool:
    """Check quota and increment if available.

    Returns ``True`` if call is allowed, ``False`` if quota exhausted.
    """
    if not is_quota_available(session):
        return False

    new_count = increment_count(session)
    cap = get_monthly_cap(session)

    if new_count % 100 == 0 or new_count >= cap - 10:
        logger.info(
            "tavily_quota_status",
            current_count=new_count,
            monthly_cap=cap,
            remaining=cap - new_count,
        )

    return True
