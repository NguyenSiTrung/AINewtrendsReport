"""Resolved LLM configuration model.

``LLMConfig`` holds the fully-resolved parameters needed to construct an
LLM client.  It is frozen (immutable) so it can be passed safely between
layers without accidental mutation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMConfig(BaseModel, frozen=True):
    """Immutable, resolved LLM configuration.

    All fields are validated at construction time. Once created the config
    cannot be modified — create a new instance via ``model_copy(update=…)``
    if you need to override values.
    """

    base_url: str
    api_key: str
    model: str

    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, gt=0)
    timeout: int = Field(default=120, gt=0)
    extra_headers: dict[str, str] | None = None

    # ── Display helpers ───────────────────────────────────

    @property
    def masked_api_key(self) -> str:
        """Return the API key with most characters replaced by ``***``.

        Keys shorter than 8 characters are fully masked.
        """
        if len(self.api_key) < 8:
            return "***"
        return f"{self.api_key[:4]}***"
