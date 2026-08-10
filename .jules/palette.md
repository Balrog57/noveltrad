## 2026-08-10 - Missing ARIA labels on icon-only buttons
**Learning:** Found a pattern where icon-only buttons using `material-symbols-outlined` or `<svg>` had `title` attributes but were missing `aria-label`s, making them inaccessible to screen readers without hovering. This occurred even when a `data-i18n-attr` was used for the title.
**Action:** Always ensure `aria-label` is explicitly set (and managed via `data-i18n-attr` if localized) on all icon-only buttons.
