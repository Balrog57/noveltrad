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

import { app } from "electron";
import { PluginHost } from "../../src/main/plugins/PluginHost";
import type { PluginServices } from "../../src/main/plugins/types";

// ── Helpers ───────────────────────────────────────────────────────────

function createTestPlugin(
  pluginsDir: string,
  id: string,
  overrides: Record<string, unknown> = {},
): string {
  const pluginDir = path.join(pluginsDir, id);
  fs.mkdirSync(pluginDir, { recursive: true });

  const manifest = {
    id,
    name: overrides.name || `Test ${id}`,
    version: (overrides.version as string) || "1.0.0",
    type: (overrides.type as string) || "export",
    entry: (overrides.entry as string) || "index.mjs",
    permissions: (overrides.permissions as string[]) || [],
    contributions: overrides.contributions || undefined,
    configSchema: overrides.configSchema || undefined,
    ...Object.fromEntries(
      Object.entries(overrides).filter(
        ([k]) => !["name", "version", "type", "entry", "permissions", "contributions", "configSchema"].includes(k),
      ),
    ),
  };

  fs.writeFileSync(path.join(pluginDir, "manifest.json"), JSON.stringify(manifest, null, 2));

  // Créer un module ESM minimal
  const entryContent = `
export default {
  manifest: ${JSON.stringify(manifest)},
  apiVersion: "1.0",
  activate: async (context) => {
    // plugin activate
  },
  deactivate: async () => {
    // plugin deactivate
  }
};
`;
  fs.writeFileSync(path.join(pluginDir, "index.mjs"), entryContent.trim());

  return pluginDir;
}

function createInvalidManifestPlugin(pluginsDir: string, id: string): string {
  const pluginDir = path.join(pluginsDir, id);
  fs.mkdirSync(pluginDir, { recursive: true });
  fs.writeFileSync(
    path.join(pluginDir, "manifest.json"),
    JSON.stringify({ id: "INVALID", name: "Test", version: "bad", type: "unknown" }, null, 2),
  );
  fs.writeFileSync(
    path.join(pluginDir, "index.mjs"),
    "export default { manifest: {}, apiVersion: '1.0', activate: async () => {}, deactivate: async () => {} };",
  );
  return pluginDir;
}

function createPluginWithoutActivate(pluginsDir: string, id: string): string {
  const pluginDir = path.join(pluginsDir, id);
  fs.mkdirSync(pluginDir, { recursive: true });
  fs.writeFileSync(
    path.join(pluginDir, "manifest.json"),
    JSON.stringify({
      id,
      name: "No Activate",
      version: "1.0.0",
      type: "export",
      entry: "index.mjs",
      permissions: [],
    }, null, 2),
  );
  fs.writeFileSync(
    path.join(pluginDir, "index.mjs"),
    "export default { manifest: {}, apiVersion: '1.0' };",
  );
  return pluginDir;
}

// ── Mocks ─────────────────────────────────────────────────────────────

const mockServices: PluginServices = {
  aiRouter: {
    chat: vi.fn(),
    streamChat: vi.fn(),
    register: vi.fn(),
    setCache: vi.fn(),
    get: vi.fn(),
    tryParseJson: vi.fn(),
    isEthicalRefusal: vi.fn(),
  } as unknown as PluginServices["aiRouter"],
  lexiconEngine: {
    load: vi.fn(),
    apply: vi.fn().mockReturnValue({ text: "", substitutions: [] }),
    extractCandidates: vi.fn(),
    exportEntries: vi.fn(),
    findConflicts: vi.fn(),
  } as unknown as PluginServices["lexiconEngine"],
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
  },
};

describe("PluginHost", () => {
  let pluginsDir: string;
  let parentDir: string;
  let host: PluginHost;

  beforeEach(() => {
    // PluginHost calcule pluginDir = app.getPath('userData') + '/plugins'
    parentDir = path.join(os.tmpdir(), `noveltrad-parent-${Date.now()}`);
    pluginsDir = path.join(parentDir, "plugins");
    fs.mkdirSync(pluginsDir, { recursive: true });
    vi.mocked(app.getPath).mockReturnValue(parentDir);
    host = new PluginHost(mockServices);
  });

  afterEach(() => {
    if (fs.existsSync(parentDir)) {
      fs.rmSync(parentDir, { recursive: true, force: true });
    }
  });

  describe("discover", () => {
    it("retourne une liste vide si aucun plugin", () => {
      const result = host.discover();
      expect(result).toEqual([]);
    });

    it("découvre un plugin valide", () => {
      createTestPlugin(pluginsDir, "com.test.valid");
      const result = host.discover();
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe("com.test.valid");
    });

    it("ignore les dossiers sans manifest.json", () => {
      const emptyDir = path.join(pluginsDir, "empty-dir");
      fs.mkdirSync(emptyDir, { recursive: true });
      const result = host.discover();
      expect(result).toHaveLength(0);
    });

    it("ignore les manifest invalides sans planter", () => {
      createInvalidManifestPlugin(pluginsDir, "com.test.invalid");
      const result = host.discover();
      expect(result).toHaveLength(0);
    });
  });

  describe("load", () => {
    it("charge un plugin valide", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.load");
      const loaded = await host.load(pluginDir);
      expect(loaded.manifest.id).toBe("com.test.load");
      expect(loaded.status).toBe("inactive");
      expect(loaded.instance).toBeDefined();
      expect(typeof loaded.instance.activate).toBe("function");
    });

    it("rejette un plugin déjà chargé", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.dup");
      await host.load(pluginDir);
      await expect(host.load(pluginDir)).rejects.toThrow("déjà chargé");
    });

    it("rejette un manifest invalide", async () => {
      const pluginDir = createInvalidManifestPlugin(pluginsDir, "com.test.bad");
      await expect(host.load(pluginDir)).rejects.toThrow();
    });

    it("rejette un plugin sans activate()", async () => {
      const pluginDir = createPluginWithoutActivate(pluginsDir, "com.test.noact");
      await expect(host.load(pluginDir)).rejects.toThrow("activate");
    });

    it("rejette un point d'entrée avec path traversal (SDD §21.3)", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.traversal", {
        entry: "../../escape.mjs",
      });
      await expect(host.load(pluginDir)).rejects.toThrow("Path traversal detected");
    });
  });

  describe("activatePlugin / deactivatePlugin / uninstallPlugin", () => {
    it("active un plugin et l'ajoute au registre", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.active");
      await host.load(pluginDir);
      await host.activatePlugin("com.test.active");
      const list = host.list();
      expect(list).toHaveLength(1);
      expect(list[0].status).toBe("active");
    });

    it("désactive un plugin avec deactivatePlugin(), le garde dans la Map", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.deact");
      await host.load(pluginDir);
      await host.activatePlugin("com.test.deact");
      await host.deactivatePlugin("com.test.deact");
      expect(host.list()).toHaveLength(1);
      expect(host.list()[0].status).toBe("inactive");
    });

    it("peut réactiver un plugin après deactivatePlugin()", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.re-activate");
      await host.load(pluginDir);
      await host.activatePlugin("com.test.re-activate");
      expect(host.list()[0].status).toBe("active");

      // Désactiver
      await host.deactivatePlugin("com.test.re-activate");
      expect(host.list()[0].status).toBe("inactive");

      // Réactiver
      await host.activatePlugin("com.test.re-activate");
      expect(host.list()[0].status).toBe("active");
    });

    it("uninstallPlugin supprime de la Map et du disque", async () => {
      const pluginDir = createTestPlugin(pluginsDir, "com.test.uninst");
      await host.load(pluginDir);
      await host.activatePlugin("com.test.uninst");

      // Vérifier que le dossier existe
      expect(fs.existsSync(pluginDir)).toBe(true);

      await host.uninstallPlugin("com.test.uninst");

      // Vérifier que le plugin est retiré de la Map
      expect(host.get("com.test.uninst")).toBeUndefined();
      expect(host.list()).toHaveLength(0);

      // Vérifier que le dossier du plugin a été supprimé
      expect(fs.existsSync(pluginDir)).toBe(false);
    });

    it("isole les erreurs de activate() sans planter", async () => {
      const pluginDir = path.join(pluginsDir, "com.test.error");
      fs.mkdirSync(pluginDir, { recursive: true });
      fs.writeFileSync(
        path.join(pluginDir, "manifest.json"),
        JSON.stringify({
          id: "com.test.error",
          name: "Error Plugin",
          version: "1.0.0",
          type: "export",
          entry: "index.mjs",
          permissions: [],
        }),
      );
      fs.writeFileSync(
        path.join(pluginDir, "index.mjs"),
        `export default {
          manifest: { id: "com.test.error", name: "Error Plugin", version: "1.0.0", type: "export" },
          apiVersion: "1.0",
          activate: async () => { throw new Error("Test error"); },
          deactivate: async () => {},
        };`,
      );
      await host.load(pluginDir);
      await host.activatePlugin("com.test.error");
      const plugin = host.get("com.test.error");
      expect(plugin?.status).toBe("error");
      expect(plugin?.errorMessage).toBeDefined();
    });

    it("active deux plugins sans conflit", async () => {
      createTestPlugin(pluginsDir, "com.test.one");
      createTestPlugin(pluginsDir, "com.test.two");
      await host.load(path.join(pluginsDir, "com.test.one"));
      await host.load(path.join(pluginsDir, "com.test.two"));
      await host.activatePlugin("com.test.one");
      await host.activatePlugin("com.test.two");
      expect(host.list()).toHaveLength(2);
    });
  });

  describe("registry", () => {
    it("getAgent retourne undefined si aucun plugin agent", () => {
      expect(host.getAgent("xianxia_check")).toBeUndefined();
    });

    it("getExport retourne undefined si aucun plugin export", () => {
      expect(host.getExport("pdf")).toBeUndefined();
    });

    it("getProvider retourne undefined si aucun plugin provider", () => {
      expect(host.getProvider("lmstudio")).toBeUndefined();
    });

    it("getParser retourne undefined si aucun plugin parser", () => {
      expect(host.getParser("pdf")).toBeUndefined();
    });
  });

  describe("init", () => {
    it("init sans plugins activés", async () => {
      const sensitive = await host.init([]);
      expect(sensitive).toEqual([]);
    });

    it("init avec plugins activés sans permissions sensibles", async () => {
      createTestPlugin(pluginsDir, "com.test.auto");
      const sensitive = await host.init(["com.test.auto"]);
      expect(sensitive).toEqual([]);
      const plugin = host.get("com.test.auto");
      expect(plugin?.status).toBe("active");
    });
  });
});
