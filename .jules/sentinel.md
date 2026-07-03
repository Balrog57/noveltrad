## 2025-02-24 - [CRITICAL] Fix IPC Context Isolation via Channel Validation
**Vulnerability:** Electron Context Isolation vulnerability where `ipcRenderer.invoke` and `ipcRenderer.on` were directly exposed to the renderer process via `contextBridge` without any validation. This allowed arbitrary access to main process functions or internal Electron IPC channels.
**Learning:** This existed because the `preload` script was acting as a simple passthrough instead of a strict mediator. It failed to implement a security boundary by blindly forwarding all requested channels to the main process.
**Prevention:** Always validate the `channel` argument in preload scripts against a strict allowlist (e.g., `IPC_CHANNELS`) before forwarding calls to `ipcRenderer` to enforce context isolation properly.
