"""SQLAlchemy ORM models — import all to ensure Base.metadata is populated."""

from ainews.models.article import Article
from ainews.models.base import Base
from ainews.models.report import Report
from ainews.models.run import Run
from ainews.models.run_log import RunLog
from ainews.models.schedule import Schedule
from ainews.models.settings_kv import SettingsKV
from ainews.models.site import Site
from ainews.models.user import User

__all__ = [
    "Article",
    "Base",
    "Report",
    "Run",
    "RunLog",
    "Schedule",
    "SettingsKV",
    "Site",
    "User",
]
