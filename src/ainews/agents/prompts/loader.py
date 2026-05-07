"""Jinja2 prompt template loader.

Templates live alongside this module in ``.j2`` files. The loader
resolves them relative to this package, renders with provided context
variables, and returns a trimmed string.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2

_TEMPLATE_DIR = Path(__file__).parent

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
    undefined=jinja2.Undefined,
)


def load_prompt(template_name: str, **context: Any) -> str:
    """Load and render a Jinja2 prompt template.

    Parameters
    ----------
    template_name
        Template basename without extension (e.g. ``"planner"``).
    **context
        Variables to pass to the template.

    Returns
    -------
    str
        Rendered prompt string.

    Raises
    ------
    FileNotFoundError
        If the template file does not exist.
    """
    filename = f"{template_name}.j2"
    template_path = _TEMPLATE_DIR / filename

    if not template_path.exists():
        msg = f"Prompt template not found: {template_name} (looked for {filename})"
        raise FileNotFoundError(msg)

    template = _env.get_template(filename)
    rendered: str = template.render(**context)
    return rendered.strip()
