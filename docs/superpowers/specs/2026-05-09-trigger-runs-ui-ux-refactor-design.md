# Trigger & Runs UI/UX Refactor — Design Spec

**Date:** 2026-05-09  
**Scope:** `trigger.html`, `runs/list.html`, `runs/detail.html`, `runs/report.html`, `partials/runs_table.html`  
**Approach:** Direct Template Replacement (copy proven Dashboard patterns, zero new abstractions)  

---

## 1. Goal

Make the Trigger Run and Pipeline Runs pages visually consistent with the Dashboard's established modern design language: rounded-2xl cards, gradient CTAs, dot-badges, uppercase tracking headers, rich empty states, and subtle hover-lift animations.

---

## 2. Design Tokens (Dashboard-Standard)

| Token | Old Value (Trigger/Runs) | New Value (Dashboard) |
|---|---|---|
| Page title size | `text-2xl` | `text-3xl` |
| Page subtitle | none | `text-sm uppercase tracking-wide` |
| Header block | `flex items-center justify-between` | `flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8` |
| Card radius | `rounded-xl` | `rounded-2xl` |
| Card shadow | `shadow-sm` | `shadow-[0_8px_30px_rgb(0,0,0,0.04)]` |
| Card dark border | none (implicit) | `dark:border dark:border-surface-800` |
| Primary button | `btn-primary` (solid) | `bg-gradient-to-r from-blue-600 to-blue-500`, `shadow-lg shadow-blue-500/30`, `hover:-translate-y-0.5` |
| Table header font | `font-medium` | `text-xs uppercase tracking-wider font-semibold` |
| Table header bg | none | `bg-surface-50/30 dark:bg-surface-800/10` |
| Table header border | `border-surface-200 dark:border-surface-700` | `border-surface-100 dark:border-surface-800` |
| Table row hover | `hover:bg-surface-50` | `hover:bg-blue-50/50 dark:hover:bg-surface-800/60` |
| Table row divider | `divide-surface-200 dark:divide-surface-700` | `divide-surface-100 dark:divide-surface-800/50` |
| Status badge radius | `rounded-full` | `rounded-md` |
| Status badge style | `badge-*` utility | Explicit inline-flex with dot indicator + semantic colors |
| Empty state | Minimal icon + text | Rich: 16 icon container, medium text, small subtext, styled CTA |

---

## 3. Per-Page Design

### 3.1 Trigger Run (`trigger.html`)

**Layout:** Remove `max-w-lg` wrapper. Keep content naturally constrained by card width (`max-w-2xl` on the card only).

**Header block:**
```
<div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
  <div>
    <p class="text-sm font-semibold text-blue-600 dark:text-cyan-400 mb-1 tracking-wide uppercase">
      Pipeline Action
    </p>
    <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">Trigger Run</h1>
  </div>
</div>
```

**Card:**
```
<div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden p-6 sm:p-8 max-w-2xl">
```

**Submit button:**
```
<button class="inline-flex items-center justify-center px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200 w-full">
  <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
  </svg>
  Start Pipeline Run
</button>
```

**Form inputs:** No change — keep `form-input` utility.

---

### 3.2 Runs List (`runs/list.html` + `partials/runs_table.html`)

**Page header:**
```
<div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
  <div>
    <p class="text-sm font-semibold text-blue-600 dark:text-cyan-400 mb-1 tracking-wide uppercase">
      Execution History
    </p>
    <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">Pipeline Runs</h1>
  </div>
  <a href="/trigger" class="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200">
    <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
    </svg>
    New Run
  </a>
</div>
```

**Outer wrapper:**
```
<div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden">
```

**Table toolbar bar (same as Dashboard):**
```
<div class="px-6 py-5 border-b border-surface-100 dark:border-surface-800 flex items-center justify-between bg-surface-50/50 dark:bg-surface-800/20">
  <h2 class="text-lg font-bold text-surface-900 dark:text-white">Recent Pipeline Runs</h2>
  <span class="text-sm font-semibold text-surface-500 dark:text-surface-400">
    Showing {{ runs|length }} of {{ total or runs|length }}
  </span>
</div>
```

**Table header row:**
```
<tr class="text-surface-500 dark:text-surface-400 bg-surface-50/30 dark:bg-surface-800/10 text-xs uppercase tracking-wider font-semibold border-b border-surface-100 dark:border-surface-800">
  <th class="px-6 py-4 text-left">Run ID</th>
  <th class="px-6 py-4 text-left">Status</th>
  <th class="px-6 py-4 text-left">Triggered By</th>
  <th class="px-6 py-4 text-left">Created</th>
  <th class="px-6 py-4 text-right">Actions</th>
</tr>
```

**Table body:**
```
<tbody class="divide-y divide-surface-100 dark:divide-surface-800/50">
  <tr class="hover:bg-blue-50/50 dark:hover:bg-surface-800/60 transition-colors group">
```

**Status badges (explicit inline):**
- `completed`: `bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400`, dot `bg-emerald-500`
- `failed`: `bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400`, dot `bg-rose-500`
- `running`: `bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400`, dot `bg-blue-500 animate-pulse`
- Other: `bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300`, dot `bg-surface-500`

**Empty state:**
```
<div class="px-6 py-16 text-center">
  <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center text-surface-400">
    <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
    </svg>
  </div>
  <p class="text-surface-500 dark:text-surface-400 font-medium">No pipeline runs yet.</p>
  <p class="text-sm text-surface-400 dark:text-surface-500 mt-1 mb-4">Your pipeline history will appear here.</p>
  <a href="/trigger" class="inline-flex items-center px-4 py-2 bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg text-sm font-medium hover:bg-surface-50 dark:hover:bg-surface-700 transition-colors shadow-sm">
    Trigger your first run
  </a>
</div>
```

---

### 3.3 Run Detail (`runs/detail.html`)

**Header block:**
```
<div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
  <div class="flex items-center gap-3">
    <a href="/runs" class="...">...</a>
    <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">
      Run <span class="font-mono text-lg text-surface-600 dark:text-surface-300">{{ run.id[:12] }}</span>
    </h1>
    <!-- status badge -->
  </div>
  <button id="btn-delete-run">...</button>
</div>
```

**Status badge:** Replace `badge-*` with explicit `rounded-md` dot badge (same token set as runs list).

**Metadata cards (4-column stat cards):**
```
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
  <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
    <div class="flex items-center justify-between mb-2">
      <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Triggered By</div>
      <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-cyan-400 shrink-0 shadow-sm">
        <!-- icon -->
      </div>
    </div>
    <div class="text-xl font-bold tracking-tight text-surface-900 dark:text-white">{{ run.triggered_by or '—' }}</div>
  </div>
  <!-- repeat for Schedule, Created, Duration/Elapsed -->
</div>
```

**Report summary card (hero gradient):**
If `report` exists, render a card matching Dashboard's "Latest Intelligence Report" hero:
```
<div class="relative overflow-hidden bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-900/10 dark:shadow-none border border-slate-700">
  <!-- decorative orbs -->
  <div class="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-blue-500/20 blur-2xl"></div>
  <div class="absolute bottom-0 left-1/2 w-48 h-48 rounded-full bg-cyan-500/10 blur-3xl"></div>
  <!-- content: icon, title, summary, stats, white CTA button -->
</div>
```

**Logs card:** Wrap in `bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px...] dark:border dark:border-surface-800 overflow-hidden p-6`.

**Delete confirmation modal:** Keep existing Alpine.js modal structure — already well-styled and consistent.

---

### 3.4 Run Report (`runs/report.html`)

**Header block:**
```
<div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
  <div class="flex items-center gap-3">
    <a href="/runs/{{ run.id }}">...</a>
    <div>
      <p class="text-sm font-semibold text-blue-600 dark:text-cyan-400 mb-1 tracking-wide uppercase">Intelligence Report</p>
      <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">{{ report.title or 'Report' }}</h1>
    </div>
    <span class="badge-success">{{ run.status }}</span>  <!-- upgrade to dot badge -->
  </div>
  <div class="flex gap-2">
    <!-- download buttons: primary gradient for .md, outlined for .xlsx -->
  </div>
</div>
```

**Content card:** `bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px...] dark:border dark:border-surface-800 overflow-hidden p-6 sm:p-8`

**Download buttons:**
- Primary (Markdown): gradient style same as other primary actions
- Secondary (Excel): outlined style `border border-surface-200 dark:border-surface-700 hover:bg-surface-100`

---

## 4. Files to Modify

| File | Lines of Change | Key Changes |
|---|---|---|
| `src/ainews/api/templates/trigger.html` | ~30 | Layout, card, button, header |
| `src/ainews/api/templates/runs/list.html` | ~20 | Header, card wrapper |
| `src/ainews/api/templates/partials/runs_table.html` | ~40 | Table header, row, badges, empty state |
| `src/ainews/api/templates/runs/detail.html` | ~60 | Header, status badge, metadata cards, report hero, logs card |
| `src/ainews/api/templates/runs/report.html` | ~25 | Header, content card, download buttons |

**No new files. No CSS changes. No backend changes.**

---

## 5. Testing Plan

1. **Visual regression:** Open `/trigger`, `/runs`, `/runs/{id}`, `/runs/{id}/report` and compare side-by-side with `/` (Dashboard)
2. **Dark mode:** Toggle dark mode on each page and verify all new tokens flip correctly
3. **Responsive:** Shrink viewport to 375px, verify stepper, table, metadata cards reflow correctly
4. **HTMX polling:** Start a run, verify table/stepper/logs still poll and re-render with new styles intact
5. **Empty states:** Temporarily clear runs table data to verify empty state renders correctly
6. **No functional changes:** Verify form submission, delete confirmation, report download all still work
