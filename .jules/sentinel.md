## 2024-05-24 - [CRITICAL] Fix IPC channel validation in preload script
**Vulnerability:** The `ipcRenderer.invoke` and `ipcRenderer.on` functions were being exposed directly to the renderer process via `contextBridge` without any validation of the `channel` parameter.
**Learning:** This could allow a compromised renderer process (e.g. via XSS) to send arbitrary IPC messages to the main process, potentially accessing internal Electron IPC channels or other privileged functions.
**Prevention:** Always validate the `channel` parameter against a strict allowlist (e.g., `IPC_CHANNELS`) in the preload script before forwarding the call to `ipcRenderer`.
