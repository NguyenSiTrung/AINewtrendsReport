"""API routes for Confluence Wiki integration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ainews.api.deps import get_db

router = APIRouter(tags=["wiki"])


@router.post("/wiki/test")
def wiki_test_connection(
    request: Request,
    session: Session = Depends(get_db),  # noqa: B008
) -> Any:
    """Test Confluence connectivity using the effective credentials.

    Reads settings from DB (``SettingsKV("wiki")``) first, falling back
    to ``AINEWS_WIKI_*`` environment variables.

    Returns JSON with ``success``, ``message``, or ``error``.
    """
    from ainews.core.config import get_wiki_settings
    from ainews.services.wiki_publisher import WikiPublisher

    wiki = get_wiki_settings(session)

    if not wiki["base_url"] or not wiki["username"]:
        return JSONResponse(
            content={
                "success": False,
                "error": "Wiki not configured. Set Base URL, Username, and Password in Settings → Wiki Integration.",
            }
        )

    publisher = WikiPublisher(
        base_url=wiki["base_url"],
        username=wiki["username"],
        password=wiki["password"],
        verify_ssl=wiki["verify_ssl"],
    )
    result = publisher.test_connection()

    if result.success:
        return JSONResponse(
            content={
                "success": True,
                "message": result.url or "Connection successful",
            }
        )

    return JSONResponse(
        content={
            "success": False,
            "error": result.error or "Connection failed",
        }
    )
