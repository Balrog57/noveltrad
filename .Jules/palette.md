## 2025-02-28 - A11y Injection in Secondary Dialogs and Tabs
**Learning:** The root application does not automatically configure accessible names, descriptions, or tooltips for custom widget subclasses inside secondary dialogs (like `ChunkDetailDialog` or `UpdateDialog`) and nested tabs (like `SettingsTab`).
**Action:** Always manually invoke the codebase's standardized `configure` method (from `src.gui.a11y`) on all interactable widgets (`QPushButton`, `QComboBox`, `QLineEdit`, etc.) to ensure comprehensive screen reader support and keyboard navigation throughout the UI.
