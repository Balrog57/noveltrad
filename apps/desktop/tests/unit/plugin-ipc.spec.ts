import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

// Mock Electron
vi.mock("electron", () => ({
  app: {
    getPath: vi.fn(),
  },
  ipcMain: {
    handle: vi.fn(),
  },
}));

// Mock electron-log
vi.mock("electron-log", () => ({
  default: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    initialize: vi.fn(),
  },
}));

import { app, ipcMain } from "electron";
import { registerPluginHandlers, setPluginHost, setSettingsManager } from "../../src/main/ipc/handlers/plugins";
import { PluginHost } from "../../src/main/plugins/PluginHost";

describe("Plugin IPC handlers", () => {
  let parentDir: string;
  let pluginsDir: string;
  let host: PluginHost;

  beforeEach(() => {
    parentDir = path.join(os.tmpdir(), `noveltrad-ipc-test-${Date.now()}`);
    pluginsDir = path.join(parentDir, "plugins");
    fs.mkdirSync(pluginsDir, { recursive: true });
    vi.mocked(app.getPath).mockReturnValue(parentDir);

    vi.mocked(ipcMain.handle).mockClear();

    host = new PluginHost({
      aiRouter: {} as any,
      lexiconEngine: {} as any,
      logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
    });

    setPluginHost(host);
    setSettingsManager({
      getAll: vi.fn().mockReturnValue({ enabledPlugins: [] }),
      set: vi.fn(),
      get: vi.fn(),
    } as any);

    registerPluginHandlers();
  });

  afterEach(() => {
    if (fs.existsSync(parentDir)) {
      fs.rmSync(parentDir, { recursive: true, force: true });
    }
  });

  it("enregistre les handlers IPC", () => {
    const channels = [
      "plugin:list",
      "plugin:enable",
      "plugin:disable",
      "plugin:uninstall",
      "plugin:install",
      "plugin:get-config",
      "plugin:set-config",
      "plugin:request-permissions",
      "plugin:confirm-permissions",
    ];

    for (const channel of channels) {
      expect(ipcMain.handle).toHaveBeenCalledWith(channel, expect.any(Function));
    }
  });

  it("plugin:list retourne un tableau vide si aucun plugin", async () => {
    // Récupérer le handler enregistré
    const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
    const listHandler = handlerCalls.find(([c]) => c === "plugin:list")![1];

    const result = await (listHandler as any)({});
    expect(result).toEqual([]);
  });

  it("plugin:install retourne 'non supporté en v1.0'", async () => {
    const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
    const installHandler = handlerCalls.find(([c]) => c === "plugin:install")![1];

    const result = await (installHandler as any)({});
    expect(result).toEqual({ success: false, error: "non supporté en v1.0" });
  });

  it("plugin:request-permissions retourne une liste vide si aucun plugin sensible", async () => {
    const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
    const permHandler = handlerCalls.find(([c]) => c === "plugin:request-permissions")![1];

    const result = await (permHandler as any)({});
    expect(result).toEqual([]);
  });

  describe("validation des entrées (SDD §21.3)", () => {
    it("plugin:enable rejette un pluginId non-string", async () => {
      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const enableHandler = handlerCalls.find(([c]) => c === "plugin:enable")![1];
      await expect((enableHandler as any)({}, 123)).rejects.toThrow();
    });

    it("plugin:disable rejette un pluginId vide", async () => {
      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const disableHandler = handlerCalls.find(([c]) => c === "plugin:disable")![1];
      await expect((disableHandler as any)({}, "")).rejects.toThrow();
    });

    it("plugin:uninstall rejette un pluginId null", async () => {
      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const uninstallHandler = handlerCalls.find(([c]) => c === "plugin:uninstall")![1];
      await expect((uninstallHandler as any)({}, null)).rejects.toThrow();
    });

    it("plugin:confirm-permissions rejette un input non-array", async () => {
      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const confirmHandler = handlerCalls.find(([c]) => c === "plugin:confirm-permissions")![1];
      await expect((confirmHandler as any)({}, "not-an-array")).rejects.toThrow();
    });

    it("plugin:set-config rejette un pluginId manquant", async () => {
      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const setConfigHandler = handlerCalls.find(([c]) => c === "plugin:set-config")![1];
      await expect((setConfigHandler as any)({}, null, { key: "value" })).rejects.toThrow();
    });
  });

  describe("plugin:enable / plugin:disable / plugin:uninstall", () => {
    it("plugin:disable appelle deactivatePlugin", async () => {
      const deactivateSpy = vi.spyOn(host, "deactivatePlugin").mockResolvedValue(undefined);

      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const disableHandler = handlerCalls.find(([c]) => c === "plugin:disable")![1];

      const result = await (disableHandler as any)({}, "test.plugin");

      expect(deactivateSpy).toHaveBeenCalledWith("test.plugin");
      expect(result).toEqual({ success: true });
    });

    it("plugin:enable appelle activatePlugin", async () => {
      // Need to have the plugin loaded so enable doesn't throw "Plugin inconnu"
      const pluginDir = path.join(pluginsDir, "test.plugin");
      fs.mkdirSync(pluginDir, { recursive: true });
      fs.writeFileSync(
        path.join(pluginDir, "manifest.json"),
        JSON.stringify({
          id: "test.plugin",
          name: "Test Plugin",
          version: "1.0.0",
          type: "export",
          entry: "index.mjs",
          permissions: [],
        }),
      );
      fs.writeFileSync(
        path.join(pluginDir, "index.mjs"),
        `export default {
          manifest: { id: "test.plugin", name: "Test Plugin", version: "1.0.0", type: "export" },
          apiVersion: "1.0",
          activate: async () => {},
          deactivate: async () => {},
        };`,
      );

      await host.load(pluginDir);

      const activateSpy = vi.spyOn(host, "activatePlugin");

      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const enableHandler = handlerCalls.find(([c]) => c === "plugin:enable")![1];

      const result = await (enableHandler as any)({}, "test.plugin");

      expect(activateSpy).toHaveBeenCalledWith("test.plugin");
      expect(result).toEqual({ success: true });
    });

    it("plugin:uninstall appelle uninstallPlugin", async () => {
      const pluginDir = path.join(pluginsDir, "test.uninst");
      fs.mkdirSync(pluginDir, { recursive: true });
      fs.writeFileSync(
        path.join(pluginDir, "manifest.json"),
        JSON.stringify({
          id: "test.uninst",
          name: "Uninstall Test",
          version: "1.0.0",
          type: "export",
          entry: "index.mjs",
          permissions: [],
        }),
      );
      fs.writeFileSync(
        path.join(pluginDir, "index.mjs"),
        `export default {
          manifest: { id: "test.uninst", name: "Uninstall Test", version: "1.0.0", type: "export" },
          apiVersion: "1.0",
          activate: async () => {},
          deactivate: async () => {},
        };`,
      );

      await host.load(pluginDir);

      const uninstallSpy = vi.spyOn(host, "uninstallPlugin");

      const handlerCalls = vi.mocked(ipcMain.handle).mock.calls;
      const uninstallHandler = handlerCalls.find(([c]) => c === "plugin:uninstall")![1];

      const result = await (uninstallHandler as any)({}, "test.uninst");

      expect(uninstallSpy).toHaveBeenCalledWith("test.uninst");
      expect(result).toEqual({ success: true });
    });
  });
});
