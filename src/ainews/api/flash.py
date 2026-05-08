"""Cookie-based flash message system for server-rendered templates.

Usage in view routes:
    flash(response, "Site created successfully", "success")
    flash(response, "Validation failed", "error")

Usage in templates (via get_flashed_messages):
    {% for msg in get_flashed_messages(request) %}
        <div class="flash flash-{{ msg.category }}">{{ msg.text }}</div>
    {% endfor %}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

FLASH_COOKIE = "_flash"


@dataclass
class FlashMessage:
    """A single flash message."""

    text: str
    category: str  # success | error | warning | info


def flash(response: Response, text: str, category: str = "info") -> None:
    """Set a flash message cookie to be displayed on the next page load."""
    msg = json.dumps({"text": text, "category": category})
    response.set_cookie(
        FLASH_COOKIE,
        msg,
        httponly=False,
        samesite="lax",
        max_age=60,  # auto-expire after 1 minute
    )


def get_flashed_messages(request: Request) -> list[FlashMessage]:
    """Read and consume flash messages from the request cookies."""
    raw = request.cookies.get(FLASH_COOKIE)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [FlashMessage(text=data["text"], category=data["category"])]
    except (json.JSONDecodeError, KeyError):
        return []
