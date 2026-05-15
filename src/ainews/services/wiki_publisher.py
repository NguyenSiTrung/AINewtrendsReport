"""Confluence Wiki publisher service.

Pushes Markdown reports to Confluence as new pages using the REST API.
Wraps content in the ``ac:structured-macro`` for Confluence's Markdown renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class WikiPublishResult:
    """Result of a wiki publish attempt."""

    success: bool
    page_id: str | None = None
    url: str | None = None
    error: str | None = None


class WikiPublisher:
    """Publish markdown reports to Confluence wiki via REST API."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        verify_ssl: bool = True,
        timeout: int = 60,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._timeout = timeout

    def publish(
        self,
        markdown_content: str,
        space_key: str,
        ancestor_id: str,
        *,
        title: str | None = None,
        title_prefix: str = "AI News, Trends",
    ) -> WikiPublishResult:
        """Push markdown to Confluence as a new page.

        Parameters
        ----------
        markdown_content
            Raw Markdown string to publish.
        space_key
            Confluence space key (e.g. ``"SVMC"``).
        ancestor_id
            Parent page ID under which the new page is created.
        title
            Explicit page title. If ``None``, auto-generated from
            *title_prefix* and the current date.
        title_prefix
            Prefix for auto-generated title (default ``"AI News, Trends"``).

        Returns
        -------
        WikiPublishResult
            Contains ``success``, ``page_id``, ``url``, or ``error``.
        """
        if not markdown_content.strip():
            return WikiPublishResult(success=False, error="Empty markdown content")

        page_title = title or self._generate_title(title_prefix)
        storage_value = self._wrap_markdown_for_confluence(markdown_content)

        payload: dict[str, Any] = {
            "type": "page",
            "title": page_title,
            "ancestors": [{"id": int(ancestor_id)}],
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": storage_value,
                    "representation": "storage",
                }
            },
        }

        api_url = f"{self._base_url}/rest/api/content/"

        log = logger.bind(
            title=page_title,
            space=space_key,
            ancestor_id=ancestor_id,
        )
        log.info("wiki_publish.start")

        try:
            response = httpx.post(
                api_url,
                json=payload,
                auth=(self._username, self._password),
                headers={"Content-Type": "application/json"},
                timeout=self._timeout,
                verify=self._verify_ssl,
            )
            response.raise_for_status()

            data = response.json()
            page_id = str(data.get("id", ""))
            page_url = self._build_page_url(data)

            log.info(
                "wiki_publish.success",
                page_id=page_id,
                url=page_url,
                status_code=response.status_code,
            )

            return WikiPublishResult(
                success=True,
                page_id=page_id,
                url=page_url,
            )

        except httpx.HTTPStatusError as exc:
            error_detail = exc.response.text[:500] if exc.response else str(exc)
            log.warning(
                "wiki_publish.http_error",
                status_code=exc.response.status_code if exc.response else None,
                error=error_detail,
            )
            return WikiPublishResult(
                success=False,
                error=f"HTTP {exc.response.status_code}: {error_detail}",
            )

        except httpx.TimeoutException:
            log.warning("wiki_publish.timeout")
            return WikiPublishResult(
                success=False,
                error=f"Request timed out after {self._timeout}s",
            )

        except Exception as exc:
            log.warning("wiki_publish.error", error=str(exc))
            return WikiPublishResult(success=False, error=str(exc))

    @staticmethod
    def _generate_title(prefix: str) -> str:
        """Generate wiki page title with current date.

        Example: ``"AI News, Trends 14 May"``
        """
        now = datetime.now()  # noqa: DTZ005
        # %-d = day without leading zero, %B = full month name
        return f"{prefix} {now.strftime('%-d %B')}"

    @staticmethod
    def _wrap_markdown_for_confluence(md: str) -> str:
        """Wrap raw Markdown in Confluence's structured-macro for rendering.

        Uses the ``markdown`` macro with ``CDATA`` wrapping to preserve
        the original Markdown content without escaping.
        """
        return (
            '<ac:structured-macro ac:name="markdown" ac:schema-version="1">'
            "<ac:plain-text-body><![CDATA["
            f"{md}"
            "]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )

    def _build_page_url(self, response_data: dict[str, Any]) -> str:
        """Build the full page URL from Confluence API response."""
        # Confluence returns _links.webui relative path
        links = response_data.get("_links", {})
        web_ui = links.get("webui", "")
        base = links.get("base", self._base_url)
        if web_ui:
            return f"{base}{web_ui}"
        # Fallback: construct from space + page ID
        page_id = response_data.get("id", "")
        return f"{self._base_url}/pages/viewpage.action?pageId={page_id}"

    def test_connection(self) -> WikiPublishResult:
        """Test connectivity to Confluence (GET current user).

        Returns
        -------
        WikiPublishResult
            ``success=True`` if auth is valid, otherwise ``error`` is set.
        """
        try:
            response = httpx.get(
                f"{self._base_url}/rest/api/user/current",
                auth=(self._username, self._password),
                timeout=15,
                verify=self._verify_ssl,
            )
            response.raise_for_status()
            data = response.json()
            username = data.get("username", data.get("displayName", "unknown"))
            return WikiPublishResult(
                success=True,
                url=f"Authenticated as: {username}",
            )
        except Exception as exc:
            return WikiPublishResult(success=False, error=str(exc))
