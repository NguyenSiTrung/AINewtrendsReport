# Product Guidelines — AI News & Trends Report

## Report Voice & Tone

### Primary Tone: Professional & Analytical
- **Neutral and objective** — Present facts without editorializing; let data speak
- **Concise** — Favor short, declarative sentences; avoid filler words
- **Actionable** — Every summary should answer "why does this matter?"
- **Source-attributed** — Always cite source outlets by name; never present synthesized content as original reporting

### Writing Rules for LLM Prompts
- Use active voice ("Google released…" not "It was released by Google…")
- Avoid superlatives ("revolutionary", "groundbreaking") unless directly quoting a source
- No first-person ("we", "our") — the report is a neutral observer
- Quantify when possible ("raised $50M" not "raised significant funding")
- Spell out acronyms on first use in each report section

### Section-Specific Guidelines

| Section | Length | Style |
|---------|--------|-------|
| Executive Summary | 3–5 sentences | High-level, no jargon, accessible to non-technical readers |
| Top Stories | 2–4 bullets per story | Factual headline + key details + "why it matters" |
| Trends | 1 paragraph per trend | Cross-reference evidence from multiple stories; identify patterns |
| Source Index | Tabular | URL, title, date, relevance score |
| Methodology | 1 paragraph | Transparent about pipeline, timeframe, source count |

## Admin UI Design Guidelines

### Visual Identity
- **Style:** Clean, functional, utilitarian — this is an internal ops tool, not a consumer product
- **Color palette:** Neutral grays with a single accent color for actions/status indicators
- **Typography:** System font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`) — no external font dependencies
- **Density:** Information-dense; favor tables and compact layouts over cards and whitespace

### UI Principles
1. **Show, don't hide** — Surface system health, last run status, and next scheduled run on the dashboard immediately
2. **One-click operations** — Triggering a run, testing LLM connection, and downloading a report should each be a single action
3. **Progressive disclosure** — List view → detail view → logs; don't overwhelm the dashboard
4. **Fail visibly** — Errors should be prominent (red status badges, inline error messages); never silently swallow failures
5. **No dark patterns** — Destructive actions (delete site, cancel run) require confirmation

### Status Indicators
| Status | Color | Icon |
|--------|-------|------|
| Success / Healthy | Green | ✅ |
| Running / In Progress | Blue | 🔄 |
| Warning / Degraded | Amber | ⚠️ |
| Failed / Error | Red | ❌ |
| Disabled / Inactive | Gray | ⏸️ |

## Report Output Standards

### Markdown Reports
- Use ATX-style headers (`#`, `##`, `###`)
- Include a YAML frontmatter block: `title`, `date`, `timeframe`, `sources_count`, `stories_count`
- Tables for structured data; bullet lists for summaries
- Horizontal rules (`---`) between major sections
- No raw HTML in Markdown output

### Excel Reports
- Sheet order: Summary → Stories → Sources → Trends
- Freeze first row (header) on all sheets
- Auto-size columns; max column width 60 characters
- Hyperlink source URLs in the Sources sheet
- Date format: `YYYY-MM-DD`

## Naming Conventions

| Item | Pattern | Example |
|------|---------|---------|
| Report file (MD) | `{YYYY-MM-DD}_{schedule_name}.md` | `2026-05-07_weekly-ai-news.md` |
| Report file (XLSX) | `{YYYY-MM-DD}_{schedule_name}.xlsx` | `2026-05-07_weekly-ai-news.xlsx` |
| Run ID | UUID v4 | `a1b2c3d4-e5f6-...` |
| Schedule name | kebab-case | `weekly-ai-news`, `monthly-trends` |
| Site category | lowercase | `research`, `industry`, `blog`, `news` |

## Error & Edge Case Handling

- **Empty results:** If no articles pass filtering, generate a short report noting "No significant AI news found for this timeframe" rather than failing silently
- **Partial failures:** If some sites fail but others succeed, produce a report with a "Degraded Sources" section listing what failed and why
- **LLM unavailable:** If the local LLM endpoint is unreachable after retries, abort the run with a clear error logged — do not produce an unsummarized report
- **Rate limiting:** Respect Tavily monthly quotas; log warnings at 80% usage; hard-stop at 95%
