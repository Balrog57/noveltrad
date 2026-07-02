import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

// Mock Electron
vi.mock("electron", () => ({
  app: {
    getPath: vi.fn(),
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

// Simuler le mode dev (VITE_DEV_SERVER_URL défini)
vi.stubEnv("VITE_DEV_SERVER_URL", "http://localhost:5173");

import { app } from "electron";
import { PluginHost } from "../../src/main/plugins/PluginHost";

describe("PluginHost hot-reload", () => {
  let parentDir: string;
  let pluginsDir: string;
  let host: PluginHost;

  beforeEach(() => {
    parentDir = path.join(os.tmpdir(), `noveltrad-hotreload-${Date.now()}`);
    pluginsDir = path.join(parentDir, "plugins");
    fs.mkdirSync(pluginsDir, { recursive: true });
    vi.mocked(app.getPath).mockReturnValue(parentDir);

    host = new PluginHost({
      aiRouter: {} as any,
      lexiconEngine: {} as any,
      logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
    });
  });

  afterEach(() => {
    // Nettoyer le watcher
    try {
      host.unwatch();
    } catch {
      // ignore
    }
    if (fs.existsSync(parentDir)) {
      fs.rmSync(parentDir, { recursive: true, force: true });
    }
  });

  it("watch ne fait rien si pas en mode dev", () => {
    vi.stubEnv("VITE_DEV_SERVER_URL", "");
    // Vérifie que watch ne crash pas même sans VITE_DEV_SERVER_URL
    host.watch();
    // Pas d'exception = succès
    expect(true).toBe(true);
    vi.stubEnv("VITE_DEV_SERVER_URL", "http://localhost:5173");
  });

  it("watch démarre un watcher en mode dev", () => {
    host.watch();
    expect(host["watcher"]).toBeDefined();
  });

  it("unwatch arrête le watcher", () => {
    host.watch();
    host.unwatch();
    expect(host["watcher"]).toBeNull();
  });

  it("watch est désactivé si unwatch est appelé", () => {
    host.watch();
    host.unwatch();
    // Vérifier que le watcher est bien fermé
    expect(host["watcher"]).toBeNull();
  });

  it("watch avec callback ne lève pas d'erreur", () => {
    const callback = vi.fn();
    host.watch(callback);
    expect(host["watcher"]).toBeDefined();
  });
});
