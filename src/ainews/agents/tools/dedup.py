"""Deduplication engine using URL canonicalization + simhash + Jaccard.

Pipeline:
1. **URL Canonicalization** — strip tracking params, normalize, resolve redirects.
2. **Simhash** — 64-bit locality-sensitive hash for fast pre-filtering.
3. **Jaccard Similarity** — token n-gram overlap for precise near-duplicate detection.
4. **Clustering** -- group duplicates, select primary by priority x recency x length.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────

# Tracking parameters to strip
_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "utm_id",
        "fbclid",
        "gclid",
        "ref",
        "source",
        "mc_cid",
        "mc_eid",
        "si",
        "icid",
        "at_xt",
        "amp",
    }
)

# AMP URL patterns to strip
_AMP_PATTERNS = [
    re.compile(r"/amp/?$"),
    re.compile(r"\.amp\.html$"),
    re.compile(r"\.amp$"),
]

# Simhash Hamming distance threshold for near-duplicate pre-filtering
_SIMHASH_THRESHOLD = 12

# Jaccard similarity threshold for confirmed near-duplicate
_JACCARD_THRESHOLD = 0.6

# Shingle size for Jaccard
_SHINGLE_SIZE = 3


# ── Models ────────────────────────────────────────────────


class Article(BaseModel):
    """Input article for deduplication."""

    url: str
    title: str
    content: str
    priority: float = 1.0
    published_at: datetime


@dataclass
class Cluster:
    """A group of deduplicated articles.

    The ``primary`` is the best representative; ``variants`` are duplicates.
    """

    primary: Article
    variants: list[Article] = field(default_factory=list)


# ── URL Canonicalization ──────────────────────────────────


def canonicalize_url(url: str) -> str:
    """Normalize and strip tracking parameters from a URL.

    - Lowercase scheme and host.
    - Strip UTM, fbclid, ref, and other tracking params.
    - Remove AMP suffixes (``/amp``, ``.amp.html``).
    - Strip trailing slash.
    """
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path

    # Strip AMP patterns
    for pattern in _AMP_PATTERNS:
        path = pattern.sub("", path)

    # Strip trailing slash
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Filter out tracking params
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {
            k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS
        }
        query = urlencode(filtered, doseq=True)
    else:
        query = ""

    return urlunparse((scheme, netloc, path, "", query, ""))


# ── Simhash ───────────────────────────────────────────────


def shingles(text: str, n: int = _SHINGLE_SIZE) -> set[str]:
    """Generate word n-gram shingles from text."""
    tokens = text.lower().split()
    if len(tokens) < n:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def simhash(text: str, hashbits: int = 64) -> int:
    """Compute a 64-bit simhash from text.

    Uses word 3-grams as features with MD5 for per-feature hashing.
    """
    v = [0] * hashbits
    tokens = shingles(text)

    for token in tokens:
        h = int(hashlib.md5(token.encode(), usedforsecurity=False).hexdigest(), 16)
        for i in range(hashbits):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1

    result = 0
    for i in range(hashbits):
        if v[i] > 0:
            result |= 1 << i
    return result


def hamming_distance(a: int, b: int) -> int:
    """Count differing bits between two integers."""
    return bin(a ^ b).count("1")


# ── Jaccard Similarity ────────────────────────────────────


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets of shingles."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ── Deduplication ─────────────────────────────────────────


def _score_article(article: Article) -> float:
    """Score an article for primary selection.

    Higher is better. Combines priority, recency, and content length.
    """
    now = datetime.now(tz=UTC)
    age_hours = max((now - article.published_at).total_seconds() / 3600, 1)
    recency = 1.0 / age_hours
    length = len(article.content)
    return article.priority * recency * (1 + length / 1000)


def deduplicate(
    articles: list[Article],
    *,
    simhash_threshold: int = _SIMHASH_THRESHOLD,
    jaccard_threshold: float = _JACCARD_THRESHOLD,
) -> list[Cluster]:
    """Cluster and deduplicate articles.

    Pipeline:
    1. Canonicalize URLs — exact URL matches cluster immediately.
    2. Compute simhash — pre-filter candidate pairs by Hamming distance.
    3. Jaccard similarity — confirm near-duplicates.
    4. Select primary per cluster by score (priority x recency x length).

    Parameters
    ----------
    articles
        List of articles to deduplicate.
    simhash_threshold
        Max Hamming distance for simhash pre-filtering (default 12).
    jaccard_threshold
        Min Jaccard similarity for confirmed duplicate (default 0.6).

    Returns
    -------
    list[Cluster]
        Deduplicated clusters with primary + variants.
    """
    if not articles:
        return []

    # Phase 1: Group by canonical URL
    url_groups: dict[str, list[int]] = {}
    for i, article in enumerate(articles):
        canonical = canonicalize_url(article.url)
        url_groups.setdefault(canonical, []).append(i)

    # Build initial clusters from URL groups
    assigned: set[int] = set()
    clusters: list[list[int]] = []

    for indices in url_groups.values():
        if len(indices) > 1:
            clusters.append(indices)
            assigned.update(indices)

    # Phase 2: Simhash + Jaccard for remaining articles
    remaining = [i for i in range(len(articles)) if i not in assigned]

    # Pre-compute simhashes and shingles
    hashes: dict[int, int] = {}
    shingle_sets: dict[int, set[str]] = {}
    for i in remaining:
        text = articles[i].title + " " + articles[i].content
        hashes[i] = simhash(text)
        shingle_sets[i] = shingles(text)

    # Find near-duplicate pairs
    used: set[int] = set()
    for idx_a in range(len(remaining)):
        i = remaining[idx_a]
        if i in used:
            continue

        cluster = [i]
        used.add(i)

        for idx_b in range(idx_a + 1, len(remaining)):
            j = remaining[idx_b]
            if j in used:
                continue

            # Fast pre-filter: simhash Hamming distance
            dist = hamming_distance(hashes[i], hashes[j])
            if dist > simhash_threshold:
                continue

            # Precise check: Jaccard similarity
            sim = jaccard_similarity(shingle_sets[i], shingle_sets[j])
            if sim >= jaccard_threshold:
                cluster.append(j)
                used.add(j)

        clusters.append(cluster)

    # Add unclustered remaining articles as singleton clusters
    for i in remaining:
        if i not in used:
            clusters.append([i])

    # Phase 3: Select primary per cluster
    result: list[Cluster] = []
    for cluster_indices in clusters:
        scored = sorted(
            cluster_indices,
            key=lambda i: _score_article(articles[i]),
            reverse=True,
        )
        primary = articles[scored[0]]
        variants = [articles[i] for i in scored[1:]]
        result.append(Cluster(primary=primary, variants=variants))

    logger.info(
        "dedup_complete",
        input_count=len(articles),
        cluster_count=len(result),
        deduped=len(articles) - len(result),
    )
    return result
