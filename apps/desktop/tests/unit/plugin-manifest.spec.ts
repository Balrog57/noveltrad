import { describe, it, expect } from "vitest";
import { pluginManifestSchema } from "@shared/schemas/plugin.js";

describe("pluginManifestSchema", () => {
  const validManifest = {
    id: "com.noveltrad.example",
    name: "Plugin exemple",
    version: "1.0.0",
    type: "export" as const,
    entry: "index.mjs",
    permissions: ["fs-write"] as const,
    contributions: {
      exports: [{ format: "pdf", name: "PDF Export" }],
    },
  };

  it("valide un manifest correct", () => {
    const result = pluginManifestSchema.parse(validManifest);
    expect(result.id).toBe("com.noveltrad.example");
    expect(result.name).toBe("Plugin exemple");
    expect(result.version).toBe("1.0.0");
    expect(result.type).toBe("export");
    expect(result.entry).toBe("index.mjs");
    expect(result.permissions).toEqual(["fs-write"]);
    expect(result.contributions?.exports).toHaveLength(1);
  });

  it("rejette un id invalide (majuscules)", () => {
    expect(() =>
      pluginManifestSchema.parse({
        ...validManifest,
        id: "Com.Noveltrad.Example",
      }),
    ).toThrow();
  });

  it("rejette un id invalide (caractères spéciaux)", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, id: "com/noveltrad/test" }),
    ).toThrow();
  });

  it("rejette un id vide", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, id: "" }),
    ).toThrow();
  });

  it("rejette une version non semver", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, version: "1.0" }),
    ).toThrow();
  });

  it("rejette une version avec pré-release", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, version: "1.0.0-beta" }),
    ).toThrow();
  });

  it("rejette un name trop long (>100)", () => {
    expect(() =>
      pluginManifestSchema.parse({
        ...validManifest,
        name: "x".repeat(101),
      }),
    ).toThrow();
  });

  it("rejette un name vide", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, name: "" }),
    ).toThrow();
  });

  it("rejette un type invalide", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, type: "invalid" }),
    ).toThrow();
  });

  it("rejette une entry .ts", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, entry: "index.ts" }),
    ).toThrow();
  });

  it("accepte une entry .js", () => {
    const result = pluginManifestSchema.parse({ ...validManifest, entry: "index.js" });
    expect(result.entry).toBe("index.js");
  });

  it("accepte une entry .mjs", () => {
    const result = pluginManifestSchema.parse({ ...validManifest, entry: "dist/index.mjs" });
    expect(result.entry).toBe("dist/index.mjs");
  });

  it("rejette une entry sans extension JS", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, entry: "index" }),
    ).toThrow();
  });

  it("rejette une entry .tsx", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, entry: "index.tsx" }),
    ).toThrow();
  });

  it("rejette une permission invalide", () => {
    expect(() =>
      pluginManifestSchema.parse({
        ...validManifest,
        permissions: ["invalid-permission"],
      }),
    ).toThrow();
  });

  it("accepte un manifest sans permissions", () => {
    const result = pluginManifestSchema.parse({
      ...validManifest,
      permissions: [],
    });
    expect(result.permissions).toEqual([]);
  });

  it("accepte un manifest sans contributions", () => {
    const result = pluginManifestSchema.parse({
      ...validManifest,
      contributions: undefined,
    });
    expect(result.contributions).toBeUndefined();
  });

  it("valide un manifest complet avec configSchema", () => {
    const result = pluginManifestSchema.parse({
      ...validManifest,
      configSchema: {
        strictness: { type: "number", default: 0.8 },
      },
    });
    expect(result.configSchema).toBeDefined();
    expect(result.configSchema?.strictness).toEqual({ type: "number", default: 0.8 });
  });

  it("valide un manifest de type agent avec contributions agents", () => {
    const result = pluginManifestSchema.parse({
      ...validManifest,
      type: "agent",
      contributions: {
        agents: [
          {
            stage: "xianxia_check",
            name: "Xianxia Check",
            description: "Vérifie la cohérence des termes de cultivation.",
          },
        ],
      },
    });
    expect(result.contributions?.agents).toHaveLength(1);
    expect(result.contributions?.agents![0].stage).toBe("xianxia_check");
  });

  it("valide un manifest de type provider avec contributions providers", () => {
    const result = pluginManifestSchema.parse({
      ...validManifest,
      type: "provider",
      contributions: {
        providers: [{ id: "lmstudio", name: "LM Studio" }],
      },
    });
    expect(result.contributions?.providers).toHaveLength(1);
  });

  it("rejette un manifest sans champs requis", () => {
    expect(() => pluginManifestSchema.parse({})).toThrow();
  });

  it("rejette un manifest null", () => {
    expect(() => pluginManifestSchema.parse(null)).toThrow();
  });

  it("rejette un manifest avec id en camelCase", () => {
    expect(() =>
      pluginManifestSchema.parse({
        ...validManifest,
        id: "com.NovelTrad.plugin",
      }),
    ).toThrow();
  });

  it("rejette un type de plugin inconnu", () => {
    expect(() =>
      pluginManifestSchema.parse({ ...validManifest, type: "theme" }),
    ).toThrow();
  });
});
