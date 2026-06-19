## 2024-06-25 - Context-Aware Accessible Names for Dynamic Table Actions
**Learning:** When generating per-row action buttons (like "Open", "Edit", or "Delete" icons) in a PyQt6 `QTableWidget`, the default accessibility name or tooltip simply reads the button text or icon, which lacks context for screen reader users traversing the table.
**Action:** Always use the custom `src.gui.a11y.configure` utility and provide a context-aware `name` and `tooltip` that incorporates the row's identifying data (e.g., `name=self.tr("Ouvrir {name}").format(name=project_name)`).
