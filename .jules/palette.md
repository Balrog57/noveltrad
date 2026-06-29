
## 2024-07-04 - Dynamic ARIA labels for list item actions
**Learning:** In PyQt6 lists or tables (like `ProjectsTab`), per-row action buttons (e.g., "Rename", "Delete") that are generated dynamically need contextual accessible names. Screen readers announcing "Delete, Button" multiple times provides no context about *what* is being deleted.
**Action:** Use `configure(widget, name=self.tr("Action {name}").format(name=item_name))` for dynamically generated per-row actions to provide clear context (e.g., "Delete Project X") for screen readers, instead of hardcoding a generic string or using `setToolTip` directly without an accessible name.
