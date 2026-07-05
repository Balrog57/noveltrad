## 2024-07-05 - Insecure IPC Payload Validation
**Vulnerability:** The Electron IPC preload script `apps/desktop/src/preload/index.ts` exposes raw `ipcRenderer.invoke` and `ipcRenderer.on` calls to the main world without validating the requested channel.
**Learning:** This breaks `contextIsolation` by allowing the renderer process (where web content might execute) to send or listen to *any* internal Electron IPC channels. It should be filtered against a strict allowlist.
**Prevention:** In Electron apps with context isolation, always define an allowlist of valid channels (e.g. `IPC_CHANNELS`) and validate the requested channel before calling `ipcRenderer` APIs in the preload script.
