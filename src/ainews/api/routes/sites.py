"""Sites CRUD router — full lifecycle management for crawlable sites."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ainews.api.deps import get_db, require_api_auth
from ainews.models.site import Site
from ainews.schemas.site import SiteCreate, SiteResponse, SiteUpdate

router = APIRouter(tags=["sites"])


def _site_to_response(site: Site) -> SiteResponse:
    return SiteResponse(
        id=site.id,
        url=site.url,
        category=site.category,
        priority=site.priority,
        crawl_depth=site.crawl_depth,
        selectors=site.selectors,
        js_render=bool(site.js_render),
        enabled=bool(site.enabled),
        created_at=site.created_at,
    )


@router.get("/sites", response_model=list[SiteResponse], dependencies=[Depends(require_api_auth)])
def list_sites(
    session: Session = Depends(get_db),  # noqa: B008
) -> list[SiteResponse]:
    """Return all sites."""
    rows = session.execute(select(Site)).scalars().all()
    return [_site_to_response(s) for s in rows]


@router.post("/sites", response_model=SiteResponse, status_code=201, dependencies=[Depends(require_api_auth)])
def create_site(
    body: SiteCreate,
    session: Session = Depends(get_db),  # noqa: B008
) -> SiteResponse:
    """Create a new site."""
    site = Site(
        url=body.url,
        category=body.category,
        priority=body.priority,
        crawl_depth=body.crawl_depth,
        selectors=body.selectors,
        js_render=int(body.js_render),
        enabled=int(body.enabled),
        created_at=datetime.now(tz=UTC).isoformat(),
    )
    try:
        session.add(site)
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Site with URL '{body.url}' already exists",
        ) from exc

    return _site_to_response(site)


@router.get("/sites/{site_id}", response_model=SiteResponse, dependencies=[Depends(require_api_auth)])
def get_site(
    site_id: int,
    session: Session = Depends(get_db),  # noqa: B008
) -> SiteResponse:
    """Return a single site by ID."""
    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return _site_to_response(site)


@router.put("/sites/{site_id}", response_model=SiteResponse, dependencies=[Depends(require_api_auth)])
def update_site(
    site_id: int,
    body: SiteUpdate,
    session: Session = Depends(get_db),  # noqa: B008
) -> SiteResponse:
    """Update an existing site (partial update)."""
    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")

    update_data = body.model_dump(exclude_unset=True)
    # Convert booleans to int for SQLite storage
    if "js_render" in update_data:
        update_data["js_render"] = int(update_data["js_render"])
    if "enabled" in update_data:
        update_data["enabled"] = int(update_data["enabled"])

    for key, value in update_data.items():
        setattr(site, key, value)

    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Site with URL '{body.url}' already exists",
        ) from exc

    return _site_to_response(site)


@router.delete("/sites/{site_id}", status_code=204, dependencies=[Depends(require_api_auth)])
def delete_site(
    site_id: int,
    session: Session = Depends(get_db),  # noqa: B008
) -> None:
    """Delete a site by ID."""
    site = session.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    session.delete(site)
