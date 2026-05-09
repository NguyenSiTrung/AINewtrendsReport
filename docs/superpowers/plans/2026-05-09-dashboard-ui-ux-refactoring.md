# Dashboard UI/UX Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the UI/UX of the Admin Dashboard into a premium, modern SaaS experience using Tailwind CSS glassmorphism, depth, and vibrant accents.

**Architecture:** We are updating the presentation layer (Jinja templates) for the base layout and the dashboard view. No backend changes are required, only HTML and Tailwind utility classes.

**Tech Stack:** HTML, Tailwind CSS, Alpine.js, HTMX

---

### Task 1: Update Global and Base Layout (`base.html`)

**Files:**
- Modify: `src/ainews/api/templates/base.html`

- [ ] **Step 1: Write the failing test (Verify current state)**

We don't need a new test, but we can run existing tests to ensure they currently pass.

Run: `pytest tests/test_admin_dashboard.py -v`
Expected: PASS

- [ ] **Step 2: Update Body Background and Sidebar**

Modify `src/ainews/api/templates/base.html` to implement the new global backgrounds and sidebar active states.

Change the `body` tag background colors to cooler slates:
```html
<body class="bg-slate-50 text-surface-900 dark:bg-slate-950 dark:text-surface-100 font-sans antialiased min-h-screen flex">
```

Modify the `nav_link` macro in `base.html` to use a gradient background and vertical border for the active state:
```html
      {% macro nav_link(label, href, icon_path) %}
        <a href="{{ href }}"
           class="group flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200
                  {% if request.url.path == href or (href != '/' and request.url.path.startswith(href)) %}
                    bg-gradient-to-r from-blue-500/10 to-cyan-400/5 text-blue-600 dark:text-cyan-400 border-l-2 border-blue-500 dark:border-cyan-400
                  {% else %}
                    text-surface-700 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-200 dark:hover:bg-surface-800 dark:hover:text-white border-l-2 border-transparent
                  {% endif %}">
          <svg class="w-5 h-5 shrink-0 transition-transform duration-200 group-hover:scale-110" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="{{ icon_path }}"/>
          </svg>
          {{ label }}
        </a>
      {% endmacro %}
```

- [ ] **Step 3: Update Profile Card in Sidebar**

Modify the bottom profile section in `base.html` to add a hover lift effect. Replace the existing User & Dark mode section:
```html
    <!-- User & Dark mode -->
    <div class="p-4 border-t border-surface-200 dark:border-surface-700 shrink-0 space-y-2 bg-slate-50/50 dark:bg-slate-900/50 backdrop-blur-sm">
      {% if request.state.user is defined and request.state.user %}
        <div class="flex items-center gap-3 px-3 py-2.5 bg-white dark:bg-surface-800 rounded-xl shadow-sm border border-surface-100 dark:border-surface-700 hover:-translate-y-0.5 transition-transform duration-200">
          <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center text-xs font-bold text-white shadow-sm">
            {{ request.state.user.email[0]|upper }}
          </div>
          <span class="flex-1 truncate text-surface-700 dark:text-surface-200 text-sm font-medium">{{ request.state.user.email }}</span>
        </div>
        <a href="/logout"
           class="group flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium text-surface-600 hover:bg-red-50 hover:text-red-600 dark:text-surface-300 dark:hover:bg-red-900/20 dark:hover:text-red-400 transition-colors">
          <svg class="w-5 h-5 group-hover:scale-110 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
          </svg>
          Logout
        </a>
      {% endif %}
      <button @click="darkMode = !darkMode"
              class="group flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm font-medium text-surface-600 hover:bg-surface-100 hover:text-surface-900 dark:text-surface-300 dark:hover:bg-surface-800 dark:hover:text-white transition-colors">
        <template x-if="!darkMode">
          <svg class="w-5 h-5 group-hover:scale-110 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
          </svg>
        </template>
        <template x-if="darkMode">
          <svg class="w-5 h-5 group-hover:scale-110 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
          </svg>
        </template>
        <span x-text="darkMode ? 'Light Mode' : 'Dark Mode'"></span>
      </button>
      <div class="mt-2 px-3 text-[10px] text-surface-400 dark:text-surface-500 font-medium tracking-wider uppercase">
        v{{ app_version }} · © {{ current_year }}
      </div>
    </div>
```

- [ ] **Step 4: Run test to verify layout didn't break functionality**

Run: `pytest tests/test_admin_dashboard.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ainews/api/templates/base.html
git commit -m "style: refactor base layout with modern sidebar and gradients"
```

---

### Task 2: Update Dashboard Header and Health Ribbon (`dashboard.html`)

**Files:**
- Modify: `src/ainews/api/templates/dashboard.html`

- [ ] **Step 1: Update Header & Greeting**

Modify the greeting and header block to integrate them smoothly.

```html
  {# ── Greeting & action ── #}
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
    <div>
      {% if request.state.user is defined and request.state.user %}
        <p class="text-sm font-semibold text-blue-600 dark:text-cyan-400 mb-1 tracking-wide uppercase">
          {{ greeting }}, Admin! 👋
        </p>
      {% endif %}
      <h1 class="text-3xl font-bold tracking-tight text-surface-900 dark:text-white">Dashboard Overview</h1>
    </div>
    
    <div class="flex items-center gap-3">
      {# System health ribbon integrated as a pill next to the trigger button #}
      {% if health_ribbon %}
      <div class="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full border backdrop-blur-md shadow-sm transition-colors duration-300
                  {% if health_ribbon.overall == 'ok' %}border-success/20 bg-success/10
                  {% elif health_ribbon.overall == 'degraded' %}border-warning/20 bg-warning/10
                  {% else %}border-danger/20 bg-danger/10{% endif %}">
        <span class="relative flex h-2.5 w-2.5">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75
                       {% if health_ribbon.overall == 'ok' %}bg-success
                       {% elif health_ribbon.overall == 'degraded' %}bg-warning
                       {% else %}bg-danger{% endif %}"></span>
          <span class="relative inline-flex rounded-full h-2.5 w-2.5
                       {% if health_ribbon.overall == 'ok' %}bg-success
                       {% elif health_ribbon.overall == 'degraded' %}bg-warning
                       {% else %}bg-danger{% endif %}"></span>
        </span>
        <span class="text-xs font-semibold tracking-wide
                    {% if health_ribbon.overall == 'ok' %}text-success-700 dark:text-success-400
                    {% elif health_ribbon.overall == 'degraded' %}text-warning-700 dark:text-warning-400
                    {% else %}text-danger-700 dark:text-danger-400{% endif %}">
          System {{ health_ribbon.overall | title }}
        </span>
      </div>
      {% endif %}

      <a href="/trigger" class="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 hover:-translate-y-0.5 transition-all duration-200">
        <svg class="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
        </svg>
        Trigger Run
      </a>
    </div>
  </div>
```
*(Remove the old standalone `# ── System health ribbon ──` block below the header as it is now integrated).*

- [ ] **Step 2: Run test to verify header changes**

Run: `pytest tests/test_admin_dashboard.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/ainews/api/templates/dashboard.html
git commit -m "style: refactor dashboard header and health ribbon"
```

---

### Task 3: Elevate Summary Cards & Latest Report (`dashboard.html`)

**Files:**
- Modify: `src/ainews/api/templates/dashboard.html`

- [ ] **Step 1: Modify Summary Cards and Latest Report Card**

Update the cards to have larger padding, rounded corners, and soft shadows. Apply a staggered animation using Alpine.js or simply add transition utilities. Also modify the Latest Report card to be a prominent Hero block.

```html
  <!-- Summary cards -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    {# Total Runs #}
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-start justify-between mb-4">
        <div>
          <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Total Runs</div>
          <div class="mt-1 text-4xl font-bold tracking-tight text-surface-900 dark:text-white">{{ stats.total_runs }}</div>
        </div>
        <div class="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 dark:text-cyan-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
        </div>
      </div>
      {% if sparkline_svg %}
      <div class="mt-4 h-12 text-blue-500/80 dark:text-cyan-400/80" title="Runs per day (last 7 days)">
        {{ sparkline_svg | safe }}
      </div>
      {% endif %}
    </div>

    {# Success Rate #}
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Success Rate</div>
          <div class="mt-1 text-4xl font-bold tracking-tight text-surface-900 dark:text-white">{{ stats.success_rate }}%</div>
        </div>
        {% if ring_svg %}
        <div class="w-16 h-16 text-emerald-500 shrink-0 drop-shadow-sm" title="{{ stats.success_rate }}% success">
          {{ ring_svg | safe }}
        </div>
        {% else %}
        <div class="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        {% endif %}
      </div>
    </div>

    {# Active Sites #}
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Active Sites</div>
        <div class="w-10 h-10 rounded-xl bg-cyan-50 dark:bg-cyan-900/20 flex items-center justify-center text-cyan-600 dark:text-cyan-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/>
          </svg>
        </div>
      </div>
      <div class="text-4xl font-bold tracking-tight text-surface-900 dark:text-white">{{ stats.active_sites }}</div>
    </div>

    {# Schedules #}
    <div class="bg-white dark:bg-surface-900 rounded-2xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 hover:-translate-y-1 transition-transform duration-300">
      <div class="flex items-center justify-between mb-4">
        <div class="text-sm font-medium text-surface-500 dark:text-surface-400">Schedules</div>
        <div class="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0 shadow-sm">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
      </div>
      <div class="text-4xl font-bold tracking-tight text-surface-900 dark:text-white">{{ stats.schedule_count }}</div>
    </div>
  </div>

  {# ── Latest Report Hero Card ── #}
  {% if latest_report_run %}
  <div class="relative overflow-hidden bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-900/10 dark:shadow-none mb-8 border border-slate-700">
    <!-- Decorative background elements -->
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
          <h2 class="text-sm font-bold text-cyan-400 uppercase tracking-widest mb-1">Latest Intelligence Report</h2>
          <p class="text-lg font-medium text-white flex items-center gap-2">
            Run <span class="font-mono bg-white/10 px-2 py-0.5 rounded text-sm">{{ latest_report_run.id[:12] }}</span>
          </p>
          <p class="text-slate-400 text-sm mt-1">Generated {{ latest_report_run.created_at[:16] if latest_report_run.created_at else '—' }}</p>
        </div>
      </div>
      <a href="/runs/{{ latest_report_run.id }}/report"
         class="inline-flex items-center px-5 py-2.5 bg-white text-slate-900 hover:bg-cyan-50 font-semibold text-sm rounded-xl shadow-lg hover:scale-105 transition-transform duration-200 shrink-0">
         View Report →
      </a>
    </div>
  </div>
  {% endif %}
```

- [ ] **Step 2: Run test to verify changes**

Run: `pytest tests/test_admin_dashboard.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/ainews/api/templates/dashboard.html
git commit -m "style: elevate dashboard summary cards and latest report hero block"
```

---

### Task 4: Polish Recent Runs Table (`dashboard.html`)

**Files:**
- Modify: `src/ainews/api/templates/dashboard.html`

- [ ] **Step 1: Modify Table Styling**

Refactor the Recent Runs table to use modern row padding, soft badges, and hover translation effects.

```html
  <!-- Recent runs table -->
  <div class="bg-white dark:bg-surface-900 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:border dark:border-surface-800 overflow-hidden">
    <div class="px-6 py-5 border-b border-surface-100 dark:border-surface-800 flex items-center justify-between bg-surface-50/50 dark:bg-surface-800/20">
      <h2 class="text-lg font-bold text-surface-900 dark:text-white">Recent Pipeline Runs</h2>
      <a href="/runs" class="text-sm font-semibold text-blue-600 hover:text-blue-700 dark:text-cyan-400 flex items-center gap-1 group">
        View all history
        <span class="group-hover:translate-x-1 transition-transform">→</span>
      </a>
    </div>
    {% if recent_runs %}
      <div class="overflow-x-auto">
        <table class="w-full text-sm text-left">
          <thead>
            <tr class="text-surface-500 dark:text-surface-400 bg-surface-50/30 dark:bg-surface-800/10 text-xs uppercase tracking-wider font-semibold border-b border-surface-100 dark:border-surface-800">
              <th class="px-6 py-4">Run ID</th>
              <th class="px-6 py-4">Status</th>
              <th class="px-6 py-4">Triggered By</th>
              <th class="px-6 py-4">Created</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-100 dark:divide-surface-800/50">
            {% for run in recent_runs %}
              <tr class="hover:bg-blue-50/50 dark:hover:bg-surface-800/60 transition-colors group">
                <td class="px-6 py-4 font-mono text-xs">
                  <a href="/runs/{{ run.id }}" class="text-surface-700 dark:text-surface-300 group-hover:text-blue-600 dark:group-hover:text-cyan-400 font-medium transition-colors">
                    {{ run.id[:12] }}…
                  </a>
                </td>
                <td class="px-6 py-4">
                  {% if run.status == 'completed' %}
                    <span class="badge-success inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                      {{ run.status | title }}
                    </span>
                  {% elif run.status == 'failed' %}
                    <span class="badge-danger inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-400">
                      <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                      {{ run.status | title }}
                    </span>
                  {% elif run.status == 'running' %}
                    <span class="badge-info inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                      <span class="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse"></span>
                      {{ run.status | title }}
                    </span>
                  {% else %}
                    <span class="badge-neutral inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-surface-100 text-surface-800 dark:bg-surface-800 dark:text-surface-300">
                      <span class="w-1.5 h-1.5 rounded-full bg-surface-500"></span>
                      {{ run.status | title }}
                    </span>
                  {% endif %}
                </td>
                <td class="px-6 py-4 text-surface-600 dark:text-surface-300">{{ run.triggered_by or '—' }}</td>
                <td class="px-6 py-4 text-surface-500 dark:text-surface-400">{{ run.created_at[:16] if run.created_at else '—' }}</td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    {% else %}
      <div class="px-6 py-16 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-surface-100 dark:bg-surface-800 flex items-center justify-center text-surface-400">
          <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
        </div>
        <p class="text-surface-500 dark:text-surface-400 font-medium">No runs yet.</p>
        <p class="text-sm text-surface-400 dark:text-surface-500 mt-1 mb-4">Your pipeline history will appear here.</p>
        <a href="/trigger" class="inline-flex items-center px-4 py-2 bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 rounded-lg text-sm font-medium hover:bg-surface-50 dark:hover:bg-surface-700 transition-colors shadow-sm">
          Trigger your first run
        </a>
      </div>
    {% endif %}
  </div>
```

- [ ] **Step 2: Run test to verify changes**

Run: `pytest tests/test_admin_dashboard.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add src/ainews/api/templates/dashboard.html
git commit -m "style: polish recent runs table with soft badges and modern styling"
```
