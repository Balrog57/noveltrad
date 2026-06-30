
## 2025-02-28 - Contextual Accessible Names in Tables
**Learning:** For QTableWidget rows where the same generic button labels (like "Edit", "Delete", or icon-only buttons) are repeated per-row, screen readers will read identically named actions, providing poor context for which item the action will modify.
**Action:** Always inject contextual values (like `{filename}` or `{project_name}`) into the accessible name of row-specific action buttons via `configure()` (e.g., `configure(btn, name=self.tr("Delete {name}").format(name=name))`).
