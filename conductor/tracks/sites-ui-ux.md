# Sites Tab UI/UX Modernization Spec

## 1. Context & Goal
The current Sites tab features a generic table layout that lacks visual harmony with the newly updated "premium, high-contrast, glassmorphic" aesthetic of the Dashboard. The goal is to refactor the Sites tab into a modern "Command Grid" that provides high legibility, reduced visual noise, and exact component-level consistency with `dashboard.html`.

## 2. Architecture & Layout
The structure will shift from a standard data table to a layered, high-contrast data stream.
- **Wrapper**: `bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800`.
- **Top Control Bar**: A unified header section with a prominent search bar and a primary call-to-action button.
- **Table Structure**: Retain the standard `<table>` markup but apply the Dashboard's padding and hover profiles.

## 3. Component Details
- **"Add Site" Button**: `bg-gradient-to-r from-blue-600 to-blue-500 rounded-xl shadow-lg shadow-blue-500/30 hover:-translate-y-0.5`.
- **Table Headers**: `bg-surface-50/30 dark:bg-surface-800/10 text-xs uppercase tracking-wider font-semibold text-surface-500`.
- **Table Rows**: Relaxed padding (`px-6 py-4`) with interactive hover states: `hover:bg-blue-50/50 dark:hover:bg-surface-800/60 transition-colors group`.
- **URL Presentation**: Full raw URLs are retained for transparency, but styled cleanly (e.g., monospace or subtle blue text) to prevent overwhelming the layout.
- **Status Badges**: 
  - Generic pills replaced with robust badges: `px-2.5 py-1 rounded-md text-xs font-semibold`.
  - The "Enabled" column will use the Dashboard's active indicator (a pulsing/solid glowing dot) alongside the text.

## 4. Action Paradigm (Hover Reveal)
To drastically reduce visual noise, the "Edit" and "Delete" actions will be hidden by default. 
- Actions will only become visible when the user hovers over a specific row, utilizing CSS `opacity-0 group-hover:opacity-100 transition-opacity`.

## 5. Scope & Trade-offs
- **In Scope**: Refactoring `sites.html` (or `sites/index.html`), updating Tailwind classes, adding the new action paradigm.
- **Out of Scope**: Changing backend API logic, adding new features to the Sites model.
- **Trade-off**: Hiding actions behind a hover reduces immediate discoverability but drastically improves scanning clarity for power users.

## 6. Testing & Validation
- Verify responsive layout (table must scroll horizontally on mobile).
- Ensure "Edit/Delete" actions are still accessible (e.g., via keyboard focus or touch devices, where hover is unavailable).
- Confirm dark mode consistency with the Dashboard colors.

---

# Sites Tab UI/UX Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Sites list interface to match the premium, high-contrast, glassmorphic aesthetic of the Dashboard.

**Architecture:** This involves modifying Tailwind CSS classes in `src/ainews/api/templates/sites/list.html` to align with `dashboard.html`. The changes involve updating container styles, unifying the header controls, replacing generic badges with robust status indicators, and introducing a hover-reveal paradigm for row actions to reduce visual clutter.

**Tech Stack:** Tailwind CSS, HTML/Jinja Templates, HTMX.

---

### Task 1: Update Page Header & Add Site Button

**Files:**
- Modify: `src/ainews/api/templates/sites/list.html:6-15`

- [ ] **Step 1: Replace header and button classes**

Update the header layout and the "Add Site" button to mirror the Dashboard's "Trigger Run" button.

```html
<div class="space-y-6">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">Sites</h1>
    </div>
    
    <div class="flex items-center gap-3">
      <a href="/sites/new" class="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200">
        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        Add Site
      </a>
    </div>
  </div>
```

- [ ] **Step 2: Commit**

```bash
git add src/ainews/api/templates/sites/list.html
git commit -m "style: update sites page header and button to match dashboard"
```

### Task 2: Refactor Table Container & Search Bar

**Files:**
- Modify: `src/ainews/api/templates/sites/list.html:17-49`

- [ ] **Step 1: Refactor search input and table wrapper**

Merge the search bar into a cohesive unit above the table, and update the table wrapper and header to match the Dashboard's "Recent Runs" table.

```html
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden">
    <div class="px-6 py-5 border-b border-surface-100 dark:border-surface-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-50/50 dark:bg-surface-800/20">
      <div class="relative max-w-md w-full">
        <input type="text"
               id="sites-search"
               value="{{ search }}"
               placeholder="Search sites…"
               class="w-full pl-10 pr-4 py-2 bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-700 rounded-xl text-sm shadow-inner focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:focus:ring-cyan-500 transition-shadow"
               hx-get="/sites"
               hx-push-url="true"
               hx-target="#sites-list-container"
               hx-swap="outerHTML"
               hx-trigger="keyup changed delay:300ms"
               name="search">
        <svg class="absolute left-3 top-2.5 w-4 h-4 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      {% if total is defined %}
        <span class="text-sm font-semibold text-surface-500 dark:text-surface-400">
          Showing {{ sites | length }} of {{ total }}
        </span>
      {% endif %}
    </div>

    <div id="sites-list-container">
      {% if sites %}
        <div class="overflow-x-auto">
          <table class="w-full text-sm text-left">
            <thead>
              <tr class="text-surface-500 dark:text-surface-400 bg-surface-50/30 dark:bg-surface-800/10 text-xs uppercase tracking-wider font-semibold border-b border-surface-100 dark:border-surface-800">
                <th class="px-6 py-4">URL</th>
                <th class="px-6 py-4">Category</th>
                <th class="px-6 py-4">Priority</th>
                <th class="px-6 py-4">Enabled</th>
                <th class="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-surface-100 dark:divide-surface-800/50">
```

- [ ] **Step 2: Commit**

```bash
git add src/ainews/api/templates/sites/list.html
git commit -m "style: refactor sites table wrapper and search bar"
```

### Task 3: Refactor Table Rows, Badges & Hover Actions

**Files:**
- Modify: `src/ainews/api/templates/sites/list.html:50-82`

- [ ] **Step 1: Apply hover styles, robust badges, and hover actions**

Update the `<tbody>` items to use hover transition states, robust Dashboard badges, and the action hover-reveal.

```html
            <tbody class="divide-y divide-surface-100 dark:divide-surface-800/50">
              {% for site in sites %}
                <tr class="hover:bg-blue-50/50 dark:hover:bg-surface-800/60 transition-colors group">
                  <td class="px-6 py-4">
                    <a href="{{ site.url }}" target="_blank" class="text-surface-700 dark:text-surface-300 group-hover:text-blue-600 dark:group-hover:text-cyan-400 font-medium transition-colors break-all flex items-center gap-2">
                      <svg class="w-4 h-4 text-surface-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      {{ site.url }}
                    </a>
                  </td>
                  <td class="px-6 py-4">
                    {% if site.category %}
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400 border border-blue-200 dark:border-blue-800/50">
                        {{ site.category | title }}
                      </span>
                    {% else %}
                      <span class="text-surface-500 dark:text-surface-400">—</span>
                    {% endif %}
                  </td>
                  <td class="px-6 py-4 font-mono text-xs font-semibold text-surface-600 dark:text-surface-300">{{ site.priority }}</td>
                  <td class="px-6 py-4">
                    {% if site.enabled is defined and not site.enabled %}
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300">
                        <span class="w-1.5 h-1.5 rounded-full bg-surface-500"></span>
                        Off
                      </span>
                    {% else %}
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                        On
                      </span>
                    {% endif %}
                  </td>
                  <td class="px-6 py-4 text-right">
                    <div class="opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-end gap-3">
                      <a href="/sites/{{ site.id }}/edit" class="text-surface-500 hover:text-blue-600 dark:hover:text-cyan-400 transition-colors" title="Edit">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </a>
                      <button hx-delete="/api/sites/{{ site.id }}"
                              hx-confirm="Delete this site?"
                              hx-target="closest tr"
                              hx-swap="outerHTML swap:0.3s"
                              class="text-surface-500 hover:text-rose-500 transition-colors" title="Delete">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
```

- [ ] **Step 2: Commit**

```bash
git add src/ainews/api/templates/sites/list.html
git commit -m "style: apply dashboard typography, robust badges, and hover actions to sites table"
```

### Task 4: Fix Empty States & Close Containers

**Files:**
- Modify: `src/ainews/api/templates/sites/list.html:86-104`

- [ ] **Step 1: Fix empty states and close the container `div` introduced in Task 2**

Wait, since I opened an extra `<div class="bg-white...` and an inner `<div id="sites-list-container">`, I need to close them properly after the pagination.

Update the tail of the file:

```html
      {% else %}
        <div class="px-6 py-16 text-center">
          <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center text-surface-400">
            <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
            </svg>
          </div>
          {% if search %}
            <p class="text-surface-500 dark:text-surface-400 font-medium">No sites match "{{ search }}".</p>
            <p class="mt-2"><a href="/sites" class="text-blue-600 hover:text-blue-700 dark:text-cyan-400 font-semibold text-sm transition-colors">Clear search</a></p>
          {% else %}
            <p class="text-surface-500 dark:text-surface-400 font-medium">No sites configured.</p>
            <p class="mt-2"><a href="/sites/new" class="text-blue-600 hover:text-blue-700 dark:text-cyan-400 font-semibold text-sm transition-colors">Add your first site →</a></p>
          {% endif %}
        </div>
      {% endif %}
      {% with base_url="/sites", query_params=query_params %}
        {% include "partials/pagination.html" %}
      {% endwith %}
    </div> <!-- Close #sites-list-container -->
  </div> <!-- Close Outer Wrapper -->
</div> <!-- Close space-y-6 -->
```

- [ ] **Step 2: Commit**

```bash
git add src/ainews/api/templates/sites/list.html
git commit -m "style: update sites empty states and fix container closures"
```
