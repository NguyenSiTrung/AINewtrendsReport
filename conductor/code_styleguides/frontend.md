# Frontend Style Guide (Jinja2 + HTMX + Tailwind + Alpine.js)

## Jinja2 Templates

### File Organization

```
src/ainews/api/templates/
├── base.html          # Base layout (head, nav, footer)
├── components/        # Reusable partials
│   ├── _status_badge.html
│   ├── _data_table.html
│   └── _flash_messages.html
├── pages/
│   ├── dashboard.html
│   ├── sites.html
│   ├── schedules.html
│   ├── runs.html
│   ├── llm_settings.html
│   └── logs.html
└── fragments/         # HTMX partial responses (no base layout)
    ├── _run_row.html
    └── _log_stream.html
```

### Conventions

- **Partials:** Prefix with underscore (`_status_badge.html`)
- **HTMX fragments:** Separate directory; these return HTML snippets, not full pages
- **Blocks:** `{% block title %}`, `{% block content %}`, `{% block scripts %}`
- **Whitespace control:** Use `{%- ... -%}` when trimming matters (tables, inline elements)

## HTMX

- **Prefer `hx-get`/`hx-post`** over custom JavaScript fetch calls
- **Use `hx-target`** to specify where the response goes
- **Use `hx-swap="innerHTML"`** for content replacement; `"outerHTML"` for full element replacement
- **Use `hx-indicator`** for loading states
- **SSE for live logs:** `hx-ext="sse"` with `sse-connect` and `sse-swap`

```html
<button hx-post="/api/trigger"
        hx-target="#run-status"
        hx-swap="innerHTML"
        hx-indicator="#spinner"
        class="btn btn-primary">
    Trigger Run
</button>
```

## Tailwind CSS

- **Use the standalone CLI** — no Node.js, no PostCSS, no build step
- **Utility-first** — compose styles in HTML, extract components for repeated patterns
- **Custom theme:** Define project colors in `tailwind.config.js` (neutral palette + single accent)
- **Responsive:** Mobile-first by default, but this is primarily a desktop admin tool

## Alpine.js

- **Use sparingly** — only for interactive UI elements that HTMX can't handle (dropdowns, modals, form toggles)
- **Keep `x-data` small** — simple boolean flags and basic state; no complex logic
- **Prefer HTMX** for server interaction; Alpine for client-only state

```html
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
    <div x-show="open" x-transition>Content</div>
</div>
```

## Accessibility

- **Semantic HTML** — use `<nav>`, `<main>`, `<section>`, `<table>` appropriately
- **ARIA labels** on icon-only buttons
- **Keyboard navigation** — all interactive elements must be tab-focusable
- **Color contrast** — meet WCAG AA for text on backgrounds
