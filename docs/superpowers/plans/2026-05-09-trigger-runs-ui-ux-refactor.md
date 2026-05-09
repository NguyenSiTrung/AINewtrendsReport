# Trigger & Runs UI/UX Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor Trigger Run and Pipeline Runs templates to match the Dashboard's modern design language (rounded-2xl cards, gradient CTAs, dot-badges, uppercase tracking headers, rich empty states).

**Architecture:** Direct template replacement. No new files, no backend changes, no CSS changes. Copy proven Dashboard CSS class patterns into 5 existing Jinja2 templates. Rebuild Tailwind output.css after all changes.

**Tech Stack:** Jinja2 templates, Tailwind CSS v4 (via `@import "tailwindcss"`), Alpine.js, HTMX, Python FastAPI backend (no backend changes).

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `src/ainews/api/templates/trigger.html` | Trigger run form page | Modify: layout, header, card, submit button |
| `src/ainews/api/templates/runs/list.html` | Runs list page shell | Modify: header, card wrapper |
| `src/ainews/api/templates/partials/runs_table.html` | Runs table HTMX partial | Modify: table header, rows, badges, empty state |
| `src/ainews/api/templates/runs/detail.html` | Run detail page | Modify: header, status badge, metadata cards, report hero, logs card |
| `src/ainews/api/templates/runs/report.html` | Run report page | Modify: header, content card, download buttons |
| `src/ainews/api/static/src/input.css` | Tailwind source | No changes — all tokens already exist |
| `src/ainews/api/static/css/output.css` | Compiled Tailwind | Rebuild after template changes |

---

### Task 1: Trigger Run Page (`trigger.html`)

**Files:**
- Modify: `src/ainews/api/templates/trigger.html`

- [ ] **Step 1: Replace page header**

Replace the current header block:
```html
<div class="max-w-lg space-y-6">
  <h1 class="text-2xl font-bold tracking-tight">Trigger Run</h1>
```

With:
```html
<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
    <div>
      <p class="text-sm font-semibold text-blue-600 dark:text-cyan-400 mb-1 tracking-wide uppercase">
        Pipeline Action
      </p>
      <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">Trigger Run</h1>
    </div>
  </div>
```

- [ ] **Step 2: Replace card wrapper**

Replace:
```html
  <div class="card">
```

With:
```html
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden p-6 sm:p-8 max-w-2xl">
```

- [ ] **Step 3: Replace submit button**

Replace:
```html
      <button type="submit" class="btn-primary w-full" :disabled="loading" :class="{ 'btn-loading': loading }">
        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" x-show="!loading">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
        </svg>
        <span x-text="loading ? 'Starting…' : 'Start Pipeline Run'"></span>
      </button>
```

With:
```html
      <button type="submit"
              class="inline-flex items-center justify-center w-full px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200"
              :disabled="loading"
              :class="{ 'btn-loading': loading }">
        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5" x-show="!loading">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
        </svg>
        <span x-text="loading ? 'Starting…' : 'Start Pipeline Run'"></span>
      </button>
```

- [ ] **Step 4: Verify closing div**

Ensure the outer `</div>` from the old `max-w-lg` wrapper is preserved as the page-level `space-y-6` container closing tag. The structure should be:
```html
<div class="space-y-6">
  <!-- header -->
  <!-- card -->
    <!-- form ... -->
  <!-- /card -->
</div>
```

- [ ] **Step 5: Commit**

```bash
git add src/ainews/api/templates/trigger.html
git commit -m "ui(trigger): modernize trigger page to match dashboard design language"
```

---

### Task 2: Runs List Page Shell (`runs/list.html`)

**Files:**
- Modify: `src/ainews/api/templates/runs/list.html`

- [ ] **Step 1: Replace page header**

Replace:
```html
  <div class="flex items-center justify-between">
    <h1 class="text-2xl font-bold tracking-tight">Pipeline Runs</h1>
    <a href="/trigger" class="btn-primary">
      <svg class="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
      </svg>
      New Run
    </a>
  </div>
```

With:
```html
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

- [ ] **Step 2: Replace card wrapper**

Replace:
```html
  <div class="card !p-0 overflow-hidden">
```

With:
```html
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden">
    <div class="px-6 py-5 border-b border-surface-100 dark:border-surface-800 flex items-center justify-between bg-surface-50/50 dark:bg-surface-800/20">
      <h2 class="text-lg font-bold text-surface-900 dark:text-white">Recent Pipeline Runs</h2>
      {% if total is defined %}
        <span class="text-sm font-semibold text-surface-500 dark:text-surface-400">Showing {{ runs|length }} of {{ total }}</span>
      {% endif %}
    </div>
```

- [ ] **Step 3: Add closing div after runs_table include**

The current code is:
```html
    {% include "partials/runs_table.html" %}
  </div>
```

This is correct — the new wrapper div added in Step 2 closes here. Verify the final structure:
```html
  <div class="bg-white dark:bg-surface-900 rounded-2xl ...">
    <div class="px-6 py-5 border-b ..."> ... </div>
    {% include "partials/runs_table.html" %}
  </div>
```

- [ ] **Step 4: Commit**

```bash
git add src/ainews/api/templates/runs/list.html
git commit -m "ui(runs-list): modernize runs list page shell to match dashboard"
```

---

### Task 3: Runs Table Partial (`partials/runs_table.html`)

**Files:**
- Modify: `src/ainews/api/templates/partials/runs_table.html`

- [ ] **Step 1: Replace table header row**

Replace:
```html
        <thead>
          <tr class="text-left text-surface-700/70 dark:text-surface-200/60 border-b border-surface-200 dark:border-surface-700">
            <th class="px-6 py-3 font-medium">Run ID</th>
            <th class="px-6 py-3 font-medium">Status</th>
            <th class="px-6 py-3 font-medium">Triggered By</th>
            <th class="px-6 py-3 font-medium">Created</th>
            <th class="px-6 py-3 font-medium text-right">Actions</th>
          </tr>
        </thead>
```

With:
```html
        <thead>
          <tr class="text-surface-500 dark:text-surface-400 bg-surface-50/30 dark:bg-surface-800/10 text-xs uppercase tracking-wider font-semibold border-b border-surface-100 dark:border-surface-800">
            <th class="px-6 py-4 text-left">Run ID</th>
            <th class="px-6 py-4 text-left">Status</th>
            <th class="px-6 py-4 text-left">Triggered By</th>
            <th class="px-6 py-4 text-left">Created</th>
            <th class="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
```

- [ ] **Step 2: Replace table body and row classes**

Replace:
```html
        <tbody class="divide-y divide-surface-200 dark:divide-surface-700">
          {% for run in runs %}
            <tr class="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
```

With:
```html
        <tbody class="divide-y divide-surface-100 dark:divide-surface-800/50">
          {% for run in runs %}
            <tr class="hover:bg-blue-50/50 dark:hover:bg-surface-800/60 transition-colors group">
```

- [ ] **Step 3: Replace status badge cells**

Replace the entire `Status` cell block for each row. Currently:
```html
              <td class="px-6 py-3">
                {% if run.status == 'completed' %}
                  <span class="badge-success">{{ run.status }}</span>
                {% elif run.status == 'failed' %}
                  <span class="badge-danger">{{ run.status }}</span>
                {% elif run.status == 'running' %}
                  <span class="badge-info">{{ run.status }}</span>
                {% else %}
                  <span class="badge-neutral">{{ run.status }}</span>
                {% endif %}
              </td>
```

With:
```html
              <td class="px-6 py-4">
                {% if run.status == 'completed' %}
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                    {{ run.status | title }}
                  </span>
                {% elif run.status == 'failed' %}
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400">
                    <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                    {{ run.status | title }}
                  </span>
                {% elif run.status == 'running' %}
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                    <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                    {{ run.status | title }}
                  </span>
                {% else %}
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300">
                    <span class="w-1.5 h-1.5 rounded-full bg-surface-500"></span>
                    {{ run.status | title }}
                  </span>
                {% endif %}
              </td>
```

- [ ] **Step 4: Update Run ID cell styling**

Replace:
```html
              <td class="px-6 py-3 font-mono text-xs">
                <a href="/runs/{{ run.id }}" class="text-primary-600 hover:underline dark:text-primary-400">
                  {{ run.id[:12] }}…
                </a>
              </td>
```

With:
```html
              <td class="px-6 py-4 font-mono text-xs">
                <a href="/runs/{{ run.id }}" class="text-surface-700 dark:text-surface-300 group-hover:text-blue-600 dark:group-hover:text-cyan-400 font-medium transition-colors">
                  {{ run.id[:12] }}…
                </a>
              </td>
```

- [ ] **Step 5: Update Triggered By and Created cell styling**

Replace:
```html
              <td class="px-6 py-3">{{ run.triggered_by or '—' }}</td>
              <td class="px-6 py-3 text-surface-700/70 dark:text-surface-200/60">
                {{ run.created_at[:16] if run.created_at else '—' }}
              </td>
```

With:
```html
              <td class="px-6 py-4 text-surface-600 dark:text-surface-300">{{ run.triggered_by or '—' }}</td>
              <td class="px-6 py-4 text-surface-500 dark:text-surface-400">
                {{ run.created_at[:16] if run.created_at else '—' }}
              </td>
```

- [ ] **Step 6: Replace empty state**

Replace:
```html
    <div class="px-6 py-12 text-center text-surface-700/50 dark:text-surface-200/40">
      <svg class="w-12 h-12 mx-auto mb-3 text-surface-700/20 dark:text-surface-200/15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
      </svg>
      <p class="font-medium text-sm">No pipeline runs yet.</p>
      <p class="mt-1 text-xs"><a href="/trigger" class="text-primary-600 hover:underline dark:text-primary-400">Trigger your first run →</a></p>
    </div>
```

With:
```html
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

- [ ] **Step 7: Commit**

```bash
git add src/ainews/api/templates/partials/runs_table.html
git commit -m "ui(runs-table): modernize table styling, badges, empty state"
```

---

### Task 4: Run Detail Page (`runs/detail.html`)

**Files:**
- Modify: `src/ainews/api/templates/runs/detail.html`

- [ ] **Step 1: Replace header block**

Replace:
```html
  <div class="flex items-center gap-3" x-data="{ confirmDelete: false }">
    <a href="/runs" class="text-surface-700/50 hover:text-surface-700 dark:text-surface-200/40 dark:hover:text-surface-200">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </a>
    <h1 class="text-2xl font-bold tracking-tight">Run <span class="font-mono text-lg">{{ run.id[:12] }}</span></h1>
```

With:
```html
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8" x-data="{ confirmDelete: false }">
    <div class="flex items-center gap-3">
      <a href="/runs" class="text-surface-700/50 hover:text-surface-700 dark:text-surface-200/40 dark:hover:text-surface-200">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </a>
      <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">
        Run <span class="font-mono text-lg text-surface-600 dark:text-surface-300">{{ run.id[:12] }}</span>
      </h1>
```

- [ ] **Step 2: Replace inline status badge**

Replace:
```html
    {% if run.status == 'completed' %}
      <span class="badge-success">{{ run.status }}</span>
    {% elif run.status == 'failed' %}
      <span class="badge-danger">{{ run.status }}</span>
    {% elif run.status == 'running' %}
      <span class="badge-info">{{ run.status }}</span>
    {% else %}
      <span class="badge-neutral">{{ run.status }}</span>
    {% endif %}
```

With:
```html
    {% if run.status == 'completed' %}
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        {{ run.status | title }}
      </span>
    {% elif run.status == 'failed' %}
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400">
        <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
        {{ run.status | title }}
      </span>
    {% elif run.status == 'running' %}
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
        <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
        {{ run.status | title }}
      </span>
    {% else %}
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300">
        <span class="w-1.5 h-1.5 rounded-full bg-surface-500"></span>
        {{ run.status | title }}
      </span>
    {% endif %}
```

- [ ] **Step 3: Replace metadata cards**

Replace the entire metadata cards grid section:
```html
  {# ── Run Metadata Cards ──────────────────────── #}
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="card">
      <div class="text-xs font-medium text-surface-700/60 dark:text-surface-200/50 uppercase">Triggered By</div>
      <div class="mt-1 font-medium">{{ run.triggered_by or '—' }}</div>
    </div>
    <div class="card">
      <div class="text-xs font-medium text-surface-700/60 dark:text-surface-200/50 uppercase">Schedule</div>
      <div class="mt-1 font-medium">{{ run.schedule_id or '—' }}</div>
    </div>
    <div class="card">
      <div class="text-xs font-medium text-surface-700/60 dark:text-surface-200/50 uppercase">Created</div>
      <div class="mt-1 font-medium">{{ run.created_at[:19] if run.created_at else '—' }}</div>
    </div>
    <div class="card" ... >
      <div class="text-xs font-medium text-surface-700/60 dark:text-surface-200/50 uppercase">
        {% if run.status in ('pending', 'running') %}Elapsed{% else %}Duration{% endif %}
      </div>
      <div class="mt-1 font-medium">
        {% if run.status in ('pending', 'running') %}
          <span x-text="elapsed" class="text-info font-mono"></span>
        {% elif run.finished_at and run.started_at %}
          {{ duration_str }}
        {% else %}
          —
        {% endif %}
      </div>
    </div>
  </div>
```

With:
```html
  {# ── Run Metadata Cards ──────────────────────── #}
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Triggered By</div>
        <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-cyan-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
          </svg>
        </div>
      </div>
      <div class="text-xl font-bold tracking-tight text-surface-900 dark:text-white">{{ run.triggered_by or '—' }}</div>
    </div>
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Schedule</div>
        <div class="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
      </div>
      <div class="text-xl font-bold tracking-tight text-surface-900 dark:text-white">{{ run.schedule_id or '—' }}</div>
    </div>
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Created</div>
        <div class="w-10 h-10 rounded-xl bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center text-cyan-600 dark:text-cyan-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
          </svg>
        </div>
      </div>
      <div class="text-xl font-bold tracking-tight text-surface-900 dark:text-white">{{ run.created_at[:19] if run.created_at else '—' }}</div>
    </div>
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300"
         {% if run.status in ('pending', 'running') %}
           x-data="{ elapsed: '', interval: null }"
           x-init="
             const start = new Date('{{ run.started_at or run.created_at }}');
             function update() {
               const now = new Date();
               const diff = Math.floor((now - start) / 1000);
               const m = Math.floor(diff / 60);
               const s = diff % 60;
               elapsed = m + 'm ' + s + 's';
             }
             update();
             interval = setInterval(update, 1000);
           "
           x-effect="if ('{{ run.status }}' !== 'running' && '{{ run.status }}' !== 'pending') { clearInterval(interval); }"
         {% endif %}>
      <div class="flex items-center justify-between mb-2">
        <div class="text-sm font-medium text-surface-500 dark:text-surface-400">
          {% if run.status in ('pending', 'running') %}Elapsed{% else %}Duration{% endif %}
        </div>
        <div class="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
      </div>
      <div class="text-xl font-bold tracking-tight text-surface-900 dark:text-white">
        {% if run.status in ('pending', 'running') %}
          <span x-text="elapsed" class="text-info font-mono"></span>
        {% elif run.finished_at and run.started_at %}
          {{ duration_str }}
        {% else %}
          —
        {% endif %}
      </div>
    </div>
  </div>
```

- [ ] **Step 4: Replace report summary card**

Replace:
```html
  {# ── Report Summary Card ───────────────────── #}
  {% if report %}
  <div class="card" id="report-summary-card">
    <div class="flex items-start gap-4">
      <div class="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center shrink-0">
        <svg class="w-5 h-5 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <h2 class="text-base font-semibold tracking-tight">{{ report.title or 'AI News Report' }}</h2>
        {% if report.summary_md %}
        <p class="mt-1 text-sm text-surface-700/60 dark:text-surface-200/50 line-clamp-3">
          {{ report.summary_md[:200] }}{% if report.summary_md|length > 200 %}…{% endif %}
        </p>
        {% endif %}
        <div class="flex flex-wrap items-center gap-3 mt-3">
          {% if report.trends %}
          <span class="text-xs font-medium text-surface-700/60 dark:text-surface-200/50">
            📊 {{ report.trends|length if report.trends is iterable and report.trends is not string else 0 }} trend(s)
          </span>
          {% endif %}
          <span class="text-xs font-medium text-surface-700/60 dark:text-surface-200/50">
            🕐 {{ report.created_at[:19] if report.created_at else '—' }}
          </span>
        </div>
      </div>
      <div class="flex flex-col sm:flex-row gap-2 shrink-0">
        <a href="/runs/{{ run.id }}/report"
           class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                  text-white bg-accent hover:bg-accent/90 transition-colors"
           id="btn-view-report">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
          </svg>
          View Full Report
        </a>
        <div class="flex gap-1">
          <a href="/runs/{{ run.id }}/report/download/md"
             class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                    border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
             title="Download Markdown" id="btn-download-md">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            .md
          </a>
          <a href="/runs/{{ run.id }}/report/download/xlsx"
             class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium
                    border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
             title="Download Excel" id="btn-download-xlsx">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            .xlsx
          </a>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
```

With:
```html
  {# ── Report Summary Card ───────────────────── #}
  {% if report %}
  <div class="relative overflow-hidden bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-900/10 dark:shadow-none border border-slate-700" id="report-summary-card">
    <div class="absolute top-0 right-0 -mr-8 -mt-8 w-32 h-32 rounded-full bg-blue-500/20 blur-2xl"></div>
    <div class="absolute bottom-0 left-1/2 w-48 h-48 rounded-full bg-cyan-500/10 blur-3xl"></div>
    <div class="relative flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
      <div class="flex items-center gap-5">
        <div class="w-14 h-14 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center shrink-0 border border-white/10 shadow-inner">
          <svg class="w-7 h-7 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <div>
          <h2 class="text-sm font-bold text-cyan-400 uppercase tracking-widest mb-1">Intelligence Report</h2>
          <p class="text-lg font-medium text-white">{{ report.title or 'AI News Report' }}</p>
          {% if report.summary_md %}
          <p class="text-slate-400 text-sm mt-1 line-clamp-2 max-w-lg">
            {{ report.summary_md[:200] }}{% if report.summary_md|length > 200 %}…{% endif %}
          </p>
          {% endif %}
          <div class="flex flex-wrap items-center gap-3 mt-3">
            {% if report.trends %}
            <span class="text-xs font-medium text-slate-400">
              📊 {{ report.trends|length if report.trends is iterable and report.trends is not string else 0 }} trend(s)
            </span>
            {% endif %}
            <span class="text-xs font-medium text-slate-400">
              🕐 {{ report.created_at[:19] if report.created_at else '—' }}
            </span>
          </div>
        </div>
      </div>
      <div class="flex flex-col sm:flex-row gap-2 shrink-0">
        <a href="/runs/{{ run.id }}/report"
           class="inline-flex items-center gap-1.5 px-5 py-2.5 bg-white text-slate-900 hover:bg-cyan-50 font-semibold text-sm rounded-xl shadow-lg hover:scale-105 transition-transform duration-200"
           id="btn-view-report">
          View Full Report →
        </a>
        <div class="flex gap-1">
          <a href="/runs/{{ run.id }}/report/download/md"
             class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 border border-slate-600 hover:bg-slate-700/50 transition-colors"
             title="Download Markdown" id="btn-download-md">
            .md
          </a>
          <a href="/runs/{{ run.id }}/report/download/xlsx"
             class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 border border-slate-600 hover:bg-slate-700/50 transition-colors"
             title="Download Excel" id="btn-download-xlsx">
            .xlsx
          </a>
        </div>
      </div>
    </div>
  </div>
  {% endif %}
```

- [ ] **Step 5: Wrap logs card in new container**

Replace:
```html
  {# ── Live Logs (HTMX polling partial) ────────── #}
  <div class="card">
    {% include "partials/run_logs.html" %}
  </div>
```

With:
```html
  {# ── Live Logs (HTMX polling partial) ────────── #}
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden p-6">
    {% include "partials/run_logs.html" %}
  </div>
```

- [ ] **Step 6: Commit**

```bash
git add src/ainews/api/templates/runs/detail.html
git commit -m "ui(run-detail): modernize header, badges, metadata cards, report hero, logs card"
```

---

### Task 5: Run Report Page (`runs/report.html`)

**Files:**
- Modify: `src/ainews/api/templates/runs/report.html`

- [ ] **Step 1: Replace header block**

Replace:
```html
  {# ── Header ──────────────────────────────────── #}
  <div class="flex flex-wrap items-center gap-3">
    <a href="/runs/{{ run.id }}" class="text-surface-700/50 hover:text-surface-700 dark:text-surface-200/40 dark:hover:text-surface-200">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
    </a>
    <h1 class="text-2xl font-bold tracking-tight">{{ report.title or 'Report' }}</h1>
    <span class="badge-success">{{ run.status }}</span>

    <div class="ml-auto flex gap-2">
      <a href="/runs/{{ run.id }}/report/download/md"
         class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
         id="btn-report-dl-md">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        Download .md
      </a>
      <a href="/runs/{{ run.id }}/report/download/xlsx"
         class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
                border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
         id="btn-report-dl-xlsx">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        Download .xlsx
      </a>
    </div>
  </div>
```

With:
```html
  {# ── Header ──────────────────────────────────── #}
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
    <div class="flex items-center gap-3">
      <a href="/runs/{{ run.id }}" class="text-surface-700/50 hover:text-surface-700 dark:text-surface-200/40 dark:hover:text-surface-200">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </a>
      <div>
        <p class="text-sm font-semibold text-blue-600 dark:text-cyan-400 mb-1 tracking-wide uppercase">Intelligence Report</p>
        <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">{{ report.title or 'Report' }}</h1>
      </div>
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        {{ run.status | title }}
      </span>
    </div>
    <div class="flex gap-2">
      <a href="/runs/{{ run.id }}/report/download/md"
         class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200"
         id="btn-report-dl-md">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        Download .md
      </a>
      <a href="/runs/{{ run.id }}/report/download/xlsx"
         class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-700/50 transition-colors"
         id="btn-report-dl-xlsx">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
        </svg>
        Download .xlsx
      </a>
    </div>
  </div>
```

- [ ] **Step 2: Replace content card wrapper**

Replace:
```html
  {# ── Report Content ──────────────────────────── #}
  <div class="card">
    <article class="prose prose-sm dark:prose-invert max-w-none report-content">
      {{ report_html | safe }}
    </article>
  </div>
```

With:
```html
  {# ── Report Content ──────────────────────────── #}
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden p-6 sm:p-8">
    <article class="prose prose-sm dark:prose-invert max-w-none report-content">
      {{ report_html | safe }}
    </article>
  </div>
```

- [ ] **Step 3: Commit**

```bash
git add src/ainews/api/templates/runs/report.html
git commit -m "ui(run-report): modernize header, card, download buttons"
```

---

### Task 6: Build Tailwind and Final Verification

**Files:**
- No file modifications (build step)

- [ ] **Step 1: Rebuild Tailwind CSS**

```bash
cd /home/trung/Documents/ML/Project/AINewtrendsReport && make css
```

Expected: `src/ainews/api/static/css/output.css` is updated with no errors.

- [ ] **Step 2: Verify server starts without template errors**

```bash
cd /home/trung/Documents/ML/Project/AINewtrendsReport && uv run python -m ainews.api.main --reload
```

Wait 5 seconds, then verify no startup errors in the logs. Ctrl+C to stop.

- [ ] **Step 3: Commit CSS rebuild**

```bash
git add src/ainews/api/static/css/output.css
git commit -m "build: recompile tailwind output.css for ui refactor"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] Trigger page header → Task 1 Step 1
- [x] Trigger page card → Task 1 Step 2
- [x] Trigger page button → Task 1 Step 3
- [x] Runs list header → Task 2 Step 1
- [x] Runs list card wrapper → Task 2 Step 2
- [x] Runs table header → Task 3 Step 1
- [x] Runs table body/row hover → Task 3 Step 2
- [x] Runs table status badges → Task 3 Step 3
- [x] Runs table Run ID styling → Task 3 Step 4
- [x] Runs table Triggered By/Created styling → Task 3 Step 5
- [x] Runs table empty state → Task 3 Step 6
- [x] Run detail header → Task 4 Step 1
- [x] Run detail status badge → Task 4 Step 2
- [x] Run detail metadata cards → Task 4 Step 3
- [x] Run detail report hero → Task 4 Step 4
- [x] Run detail logs card → Task 4 Step 5
- [x] Run report header → Task 5 Step 1
- [x] Run report content card → Task 5 Step 2
- [x] Tailwind rebuild → Task 6

**2. Placeholder scan:**
- [x] No "TBD", "TODO", "implement later"
- [x] No vague "add error handling" without specifics
- [x] Every code step contains exact HTML to paste
- [x] No "similar to Task N" references

**3. Type consistency:**
- [x] All status badges use same dot-badge pattern across Task 3, Task 4, Task 5
- [x] All cards use same `rounded-2xl` + `shadow-[0_8px_30px...]` + `dark:border` pattern
- [x] All buttons use same gradient pattern
- [x] All headers use same `flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8` pattern

**4. No backend changes:** Verified — all tasks modify Jinja2 templates only.

**5. No new files:** Verified — only modifications to existing 5 template files.
