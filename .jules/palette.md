## 2024-05-24 - Accessible names on nested navigation buttons
**Learning:** Icon-only navigation buttons in nested editor views (like the Style Editor's "arrow_back" button) are easily missed during a11y reviews. They critically require both `aria-label` for screen readers and `title` for mouse users since they lack textual context.
**Action:** Always verify icon-only buttons have proper accessible names and tooltips using the `data-i18n-attr` pattern.
