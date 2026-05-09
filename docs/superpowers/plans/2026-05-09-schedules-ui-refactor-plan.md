# Schedules UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Schedules UI list view to match the premium, glassmorphic "Data Stream" aesthetic of the Sites and Dashboard tabs.

**Architecture:** Use Tailwind CSS to replace the generic table layout with a styled `rounded-2xl` data stream container, pulsating vitality core status badges, sleek monospace tech pills, and hover-reveal action icons.

**Tech Stack:** HTML, Tailwind CSS, Jinja2 Templates, HTMX.

---

### Task 1: Update Wrapper, Header, and Empty State

**Files:**
- Modify: `src/ainews/api/templates/schedules/list.html`

- [ ] **Step 1: Update Header and Add Button**

Update the header section to use `text-3xl tracking-tight` and the premium gradient button.
```html
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">Schedules</h1>
    </div>
    
    <div class="flex items-center gap-3">
      <a href="/schedules/new" class="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200">
        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
        </svg>
        Add Schedule
      </a>
    </div>
  </div>
```

- [ ] **Step 2: Update Main Card Wrapper**

Replace `<div class="card !p-0 overflow-hidden">` with the new data stream wrapper.
```html
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden">
```

- [ ] **Step 3: Update Empty State**

Replace the current empty state with a polished, rounded icon design.
```html
    {% else %}
      <div class="px-6 py-16 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center text-surface-400">
          <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <p class="text-surface-500 dark:text-surface-400 font-medium">No schedules configured.</p>
        <p class="mt-2"><a href="/schedules/new" class="text-blue-600 hover:text-blue-700 dark:text-cyan-400 font-semibold text-sm transition-colors">Create your first schedule →</a></p>
      </div>
    {% endif %}
```

- [ ] **Step 4: Review changes visually and Commit**

```bash
git add src/ainews/api/templates/schedules/list.html
git commit -m "style(schedules): upgrade header, wrapper, and empty state"
```

### Task 2: Refactor Table Headers and Row Structure

**Files:**
- Modify: `src/ainews/api/templates/schedules/list.html`

- [ ] **Step 1: Update Table Header Styles**

Replace the generic `<thead>` styles with uppercase tracking-wider styles.
```html
          <thead>
            <tr class="text-surface-500 dark:text-surface-400 bg-surface-50/30 dark:bg-surface-800/10 text-xs uppercase tracking-wider font-semibold border-b border-surface-100 dark:border-surface-800">
              <th class="px-6 py-4">Name</th>
              <th class="px-6 py-4">Cron Expression</th>
              <th class="px-6 py-4 text-center">Timeframe (days)</th>
              <th class="px-6 py-4">Status</th>
              <th class="px-6 py-4 text-right">Actions</th>
            </tr>
          </thead>
```

- [ ] **Step 2: Update Table Body and Row Hover Styles**

Replace the generic `<tbody>` and `<tr>` classes. Add `group` class to `<tr>` for the hover-reveal actions later.
```html
          <tbody class="divide-y divide-surface-100 dark:divide-surface-800/50">
            {% for sched in schedules %}
              <tr class="hover:bg-blue-50/50 dark:hover:bg-surface-800/60 transition-colors group">
                <td class="px-6 py-4 font-medium text-surface-900 dark:text-white">{{ sched.name }}</td>
                <td class="px-6 py-4 font-mono text-xs">{{ sched.cron_expr }}</td>
                <td class="px-6 py-4">{{ sched.timeframe_days }}</td>
                <td class="px-6 py-4">
                  {% if sched.enabled is defined and not sched.enabled %}
                    <span class="badge-danger">Off</span>
                  {% else %}
                    <span class="badge-success">On</span>
                  {% endif %}
                </td>
                <td class="px-6 py-4 text-right space-x-2">
                  <a href="/schedules/{{ sched.id }}/edit" class="text-sm text-primary-600 hover:underline dark:text-primary-400">Edit</a>
                  <button hx-delete="/api/schedules/{{ sched.id }}"
                          hx-confirm="Delete this schedule?"
                          hx-target="closest tr"
                          hx-swap="outerHTML swap:0.3s"
                          class="text-sm text-danger hover:underline">Delete</button>
                </td>
              </tr>
            {% endfor %}
          </tbody>
```

- [ ] **Step 3: Review changes visually and Commit**

```bash
git add src/ainews/api/templates/schedules/list.html
git commit -m "style(schedules): refactor table header and row hover styles"
```

### Task 3: Implement Data Pills and Vitality Core Status

**Files:**
- Modify: `src/ainews/api/templates/schedules/list.html`

- [ ] **Step 1: Update Cron Expression Pill**

Replace the raw text cron expression with a styled monospace pill.
```html
                <td class="px-6 py-4">
                  <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-mono font-semibold bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300 border border-surface-200 dark:border-surface-700">
                    {{ sched.cron_expr }}
                  </span>
                </td>
```

- [ ] **Step 2: Update Timeframe Style**

Style the timeframe to match a data metric.
```html
                <td class="px-6 py-4 text-center">
                  <span class="text-sm font-semibold text-surface-600 dark:text-surface-400">{{ sched.timeframe_days }}</span>
                </td>
```

- [ ] **Step 3: Implement Vitality Core Status Badges**

Replace the old Enabled status with the pulsating On/Off badges.
```html
                <td class="px-6 py-4">
                  {% if sched.enabled is defined and not sched.enabled %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300">
                      <span class="w-1.5 h-1.5 rounded-full bg-surface-500"></span>
                      Off
                    </span>
                  {% else %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                      Active
                    </span>
                  {% endif %}
                </td>
```

- [ ] **Step 4: Review changes visually and Commit**

```bash
git add src/ainews/api/templates/schedules/list.html
git commit -m "style(schedules): implement tech pills and vitality core status badges"
```

### Task 4: Implement Hover-Reveal Actions

**Files:**
- Modify: `src/ainews/api/templates/schedules/list.html`

- [ ] **Step 1: Replace text links with SVG icons using hover-reveal**

Update the Actions `<td>` to use flexbox, hide the icons initially, and reveal them on row hover.
```html
                <td class="px-6 py-4 text-right">
                  <div class="flex items-center justify-end gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <a href="/schedules/{{ sched.id }}/edit" class="text-surface-400 hover:text-blue-600 dark:text-surface-500 dark:hover:text-cyan-400 transition-colors" title="Edit">
                      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </a>
                    <button hx-delete="/api/schedules/{{ sched.id }}"
                            hx-confirm="Delete this schedule?"
                            hx-target="closest tr"
                            hx-swap="outerHTML swap:0.3s"
                            class="text-surface-400 hover:text-rose-500 dark:text-surface-500 transition-colors" title="Delete">
                      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
```

- [ ] **Step 2: Review changes visually and Commit**

```bash
git add src/ainews/api/templates/schedules/list.html
git commit -m "style(schedules): implement hover-reveal action icons"
```

### Task 5: Align Form Styling (Optional/Cleanup)

**Files:**
- Modify: `src/ainews/api/templates/schedules/form.html`

- [ ] **Step 1: Align form header and layout**

Ensure the `form.html` header uses the updated typography.
```html
<div class="max-w-xl mx-auto space-y-6">
  <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">{{ "Edit Schedule" if schedule else "New Schedule" }}</h1>

  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 p-6 md:p-8">
    <form method="POST" action="{{ '/schedules/' ~ schedule.id if schedule else '/schedules/new' }}" class="space-y-5" x-data="{ loading: false }" @submit="loading = true">
```

- [ ] **Step 2: Review and commit**

```bash
git add src/ainews/api/templates/schedules/form.html
git commit -m "style(schedules): align form typography and card container"
```
