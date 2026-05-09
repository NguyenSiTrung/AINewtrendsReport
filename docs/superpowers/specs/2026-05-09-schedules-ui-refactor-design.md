# Schedules Tab UI/UX Refactor Design

## Context
The current Schedules tab (`src/ainews/api/templates/schedules/list.html`) uses a generic, boilerplate HTML table that feels static and disconnected from the recently modernized premium, "glassmorphic" aesthetic of the Dashboard and Sites tabs. This refactor aims to elevate the Schedules page to a modern SaaS standard.

## Scope
This design covers the UI/UX refactoring of the Schedules tab list view, with potential minor style alignments to the `form.html` if necessary. No backend changes or new features are included in this scope.

## Architecture & Layout
- **High-Contrast Data Stream:** The flat table container will be replaced with a sleek "Data Stream" structure.
- **Wrapper:** The table will be wrapped in a premium `rounded-2xl` container with subtle diffusion shadows (`shadow-[0_8px_30px_rgb(0,0,0,0.04)]`) and crisp 1px borders for dark mode, directly matching the Sites tab (`bg-white dark:bg-surface-900`).
- **Row Interaction:** Each row will have subtle background transitions (`hover:bg-blue-50/50 dark:hover:bg-surface-800/60`) to create a magnetic feel on hover.

## Components & Data Display

### Typography & Header Hierarchy
- The main `h1` will be updated to `text-3xl font-bold tracking-tight text-surface-900 dark:text-white`.
- The `+ Add Schedule` button will be upgraded to a premium gradient button (`bg-gradient-to-r from-blue-600 to-blue-500`) with hover-translate micro-animations and drop shadows (`shadow-blue-500/30`), replacing the basic flat button.

### The "Vitality Core" (Status Badges)
- The static `badge-success` and `badge-danger` text pills will be replaced.
- Active schedules will feature a pulsating dot (`animate-pulse`) inside an emerald/surface-styled badge (`bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400`), making the system feel "alive".
- Inactive schedules will use a subdued gray badge with a static dot.

### Data Presentation (The Tech Pill)
- Cron expressions (e.g., `0 7 * * 1`) will be encased in a technical monospace pill layout with a distinct contrasting background (e.g., dark slate/blue). 
- If technically feasible within the template without backend changes, a "Split Tech Pill" approach will be used (showing both raw cron and a human-readable summary). Otherwise, a highly stylized raw tech pill will be implemented to emphasize it as a system parameter.

### Hover-Reveal Actions
- The explicit "Edit Delete" text links will be eliminated to reduce visual clutter.
- Clean SVG icons (pencil for edit, trash for delete) will be positioned at the extreme right of each row.
- These icons will utilize a hover-reveal paradigm, remaining subdued (`text-surface-400`) until the user hovers over the row, at which point they transition colors (`hover:text-blue-600` / `hover:text-rose-500`).

### Polished Empty State
- The "No schedules configured" view will be upgraded with a centered, rounded-full icon container, improved spacing, and inviting typography to match the Sites tab's empty state.

## Implementation Details
The changes will be applied primarily to `src/ainews/api/templates/schedules/list.html` using Tailwind CSS classes. Existing HTMX logic for deletions and routing for editing/creation will remain exactly as they are.
