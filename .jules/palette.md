# Palette's Journal

Critical UX/accessibility learnings for NovelTrad. Routine improvements are not logged here.

## 2026-09-09 - File upload drop zones are div-onclick traps
**Learning:** The Translate, Refine, and Sample file pickers used `<div onclick>` with no `tabindex`, keyboard handler, or `aria-label`. Mouse users could browse files; keyboard and screen-reader users could not reach them at all.
**Action:** Treat every `.file-upload` zone like an interactive control: `role="button"`, `tabindex="0"`, reactive `aria-label` from existing drop-zone copy, Enter/Space → hidden `<input type="file">`, plus `:focus-visible`. When adding a new upload zone, wire keyboard in the same module that owns drag-drop.
**Learning:** Settings, Notifications, and Activity Log collapsibles were `<div onclick>` headers — invisible to keyboard and screen readers. The `.prompt-options-toggle` pattern should be `<button type="button">` with `aria-expanded` / `aria-controls`, plus `button.prompt-options-toggle` reset styles and `:focus-visible`.
**Action:** When touching any collapsible header, convert div → button and sync `aria-expanded` in the toggle handler. All three Settings-tab collapsibles (Provider & Defaults, Notifications, Activity Log) now follow this pattern.