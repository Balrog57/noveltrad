# Palette's Journal

Critical UX/accessibility learnings for NovelTrad. Routine improvements are not logged here.

## 2026-08-25 - Collapsible section toggles use non-focusable divs
**Learning:** Settings, Notifications, and Activity Log collapsibles were `<div onclick>` headers — invisible to keyboard and screen readers. The `.prompt-options-toggle` pattern should be `<button type="button">` with `aria-expanded` / `aria-controls`, plus `button.prompt-options-toggle` reset styles and `:focus-visible`.
**Action:** When touching any collapsible header, convert div → button and sync `aria-expanded` in the toggle handler. All three Settings-tab collapsibles (Provider & Defaults, Notifications, Activity Log) now follow this pattern.

## 2026-09-08 - File upload drop zones need role="button" + keyboard activation
**Learning:** The three `.file-upload` drop zones (Translate, Refine, Sample) were `<div onclick>` — invisible to keyboard users and screen readers. They need `role="button"`, `tabindex="0"`, a translated `aria-label`, Enter/Space handlers, and `:focus-visible` styling. Click activation belongs in JS (not inline onclick) so nested controls (e.g. the Refine mode `<select>`) can be excluded via `ignoreSelector`.
**Action:** Use `bindUploadZoneActivation()` in `file-upload.js` for new drop zones; mirror the pattern in `sample-manager.js` for the Sample tab zone.