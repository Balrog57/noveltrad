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
import { ExportEngine } from "../../src/main/services/ExportEngine";

describe("Example Export PDF plugin", () => {
  let parentDir: string;
  let pluginsDir: string;

  beforeEach(() => {
    parentDir = path.join(os.tmpdir(), `noveltrad-example-${Date.now()}`);
    pluginsDir = path.join(parentDir, "plugins");
    fs.mkdirSync(pluginsDir, { recursive: true });
    vi.mocked(app.getPath).mockReturnValue(parentDir);
  });

  afterEach(() => {
    if (fs.existsSync(parentDir)) {
      fs.rmSync(parentDir, { recursive: true, force: true });
    }
  });

  it("le manifest du plugin exemple est valide", async () => {
    const manifestPath = path.resolve(
      __dirname,
      "../../../../plugins/example-export-pdf/manifest.json",
    );
    const raw = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));

    // Validation directe via le schéma Zod
    const { pluginManifestSchema } = await import("@shared/schemas/plugin.js");
    const result = pluginManifestSchema.parse(raw);

    expect(result.id).toBe("com.noveltrad.example-export");
    expect(result.type).toBe("export");
    expect(result.entry).toBe("index.mjs");
    expect(result.permissions).toContain("fs-write");
    expect(result.contributions?.exports).toHaveLength(1);
    expect(result.contributions?.exports![0].format).toBe("pdf");
  });

  it("le plugin peut être chargé et activé dans PluginHost", async () => {
    const exportEngine = new ExportEngine();

    const host = new PluginHost(
      {
        aiRouter: {} as any,
        lexiconEngine: {} as any,
        logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
      },
      exportEngine,
    );

    // Copier le plugin dans le dossier plugins/
    const srcDir = path.resolve(
      __dirname,
      "../../../../plugins/example-export-pdf",
    );
    const destDir = path.join(pluginsDir, "com.noveltrad.example-export");
    fs.cpSync(srcDir, destDir, { recursive: true });

    // Charger et activer
    await host.load(destDir);
    await host.activatePlugin("com.noveltrad.example-export");

    const plugin = host.get("com.noveltrad.example-export");
    expect(plugin?.status).toBe("active");
  });

  it("le plugin enregistre un export pdf dans ExportEngine", async () => {
    const exportEngine = new ExportEngine();
    const registerSpy = vi.spyOn(exportEngine, "registerRenderer");

    const host = new PluginHost(
      {
        aiRouter: {} as any,
        lexiconEngine: {} as any,
        logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
      },
      exportEngine,
    );

    const srcDir = path.resolve(
      __dirname,
      "../../../../plugins/example-export-pdf",
    );
    const destDir = path.join(pluginsDir, "com.noveltrad.example-export");
    fs.cpSync(srcDir, destDir, { recursive: true });

    await host.load(destDir);
    await host.activatePlugin("com.noveltrad.example-export");

    // Vérifier que le plugin a enregistré le renderer
    const hostExport = host.getExport("pdf");
    expect(hostExport).toBeDefined();
  });

  it("l'ExportEngine utilise le renderer enregistré par le plugin via PluginContext", async () => {
    const exportEngine = new ExportEngine();

    const host = new PluginHost(
      {
        aiRouter: {} as any,
        lexiconEngine: {} as any,
        logger: { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() },
      },
      exportEngine,
    );

    // Créer un plugin qui enregistre un export "pdf" pendant activate()
    const pluginDir = path.join(pluginsDir, "com.test.integration");
    fs.mkdirSync(pluginDir, { recursive: true });
    fs.writeFileSync(
      path.join(pluginDir, "manifest.json"),
      JSON.stringify({
        id: "com.test.integration",
        name: "Integration Test",
        version: "1.0.0",
        type: "export",
        entry: "index.mjs",
        permissions: [],
      }),
    );
    fs.writeFileSync(
      path.join(pluginDir, "index.mjs"),
      `export default {
        manifest: { id: "com.test.integration", name: "Integration Test", version: "1.0.0", type: "export" },
        apiVersion: "1.0",
        activate: async (context) => {
          context.registerExport("pdf", async (input) => {
            return Buffer.from("pdf-from-plugin:" + input.format);
          });
        },
        deactivate: async () => {},
      };`,
    );

    await host.load(pluginDir);
    await host.activatePlugin("com.test.integration");

    // Vérifier que l'ExportEngine a bien le renderer via la connexion automatique
    const result = await (exportEngine as any)["render"]({
      projectId: "test",
      title: "Test",
      paragraphs: [],
      format: "pdf",
    });

    expect(Buffer.isBuffer(result)).toBe(true);
    expect(result.toString()).toBe("pdf-from-plugin:pdf");
  });
});
