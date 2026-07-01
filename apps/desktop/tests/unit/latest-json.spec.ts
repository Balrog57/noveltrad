import { describe, it, expect } from "vitest";
import { writeFileSync, mkdtempSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createHash } from "node:crypto";
import { generateLatestJson } from "@scripts/generate-latest-json";

describe("generateLatestJson", () => {
  /** Crée un dossier temporaire avec un faux installateur */
  function createFakeInstaller(
    name = "NovelTrad-Setup-2.0.1.exe",
    content = "fake installer content",
  ): string {
    const tmpDir = mkdtempSync(join(tmpdir(), "noveltrad-test-json-"));
    const installerPath = join(tmpDir, name);
    writeFileSync(installerPath, content);
    return installerPath;
  }

  // ── Champs obligatoires ──────────────────────────────────────────

  it("devrait générer un manifeste avec tous les champs requis", () => {
    const installerPath = createFakeInstaller();
    const manifest = generateLatestJson({ version: "2.0.1", installerPath });

    expect(manifest.version).toBe("2.0.1");
    expect(manifest.channel).toBe("stable");
    expect(typeof manifest.release_date).toBe("string");
    // Vérifie que release_date est une date ISO valide
    expect(() => new Date(manifest.release_date)).not.toThrow();
    expect(manifest.download_url).toBe(
      "https://github.com/Balrog57/noveltrad/releases/download/v2.0.1/NovelTrad-Setup-2.0.1.exe",
    );
    expect(manifest.release_notes_url).toBe(
      "https://github.com/Balrog57/noveltrad/releases/tag/v2.0.1",
    );
    expect(manifest.sha256).toBeTruthy();
    expect(manifest.mandatory).toBe(false);
    expect(manifest.min_app_version).toBe("1.0.0");
  });

  // ── SHA256 ──────────────────────────────────────────────────────

  it("devrait calculer le SHA256 correct du fichier", () => {
    const content = "test content for sha256 verification";
    const installerPath = createFakeInstaller("setup.exe", content);

    const manifest = generateLatestJson({ version: "1.0.0", installerPath });
    const expectedHash = createHash("sha256").update(content).digest("hex");

    expect(manifest.sha256).toBe(expectedHash);
  });

  it("devrait produire un SHA256 différent pour un contenu différent", () => {
    const installerPath1 = createFakeInstaller("a.exe", "content A");
    const installerPath2 = createFakeInstaller("b.exe", "content B");

    const manifestA = generateLatestJson({ version: "1.0.0", installerPath: installerPath1 });
    const manifestB = generateLatestJson({ version: "1.0.0", installerPath: installerPath2 });

    expect(manifestA.sha256).not.toBe(manifestB.sha256);
  });

  // ── Channel ─────────────────────────────────────────────────────

  it("devrait utiliser 'stable' comme channel par défaut", () => {
    const installerPath = createFakeInstaller();
    const manifest = generateLatestJson({ version: "1.0.0", installerPath });
    expect(manifest.channel).toBe("stable");
  });

  it("devrait accepter un channel beta", () => {
    const installerPath = createFakeInstaller();
    const manifest = generateLatestJson({
      version: "2.0.1-beta.1",
      installerPath,
      channel: "beta",
    });
    expect(manifest.channel).toBe("beta");
  });

  it("devrait accepter un channel alpha", () => {
    const installerPath = createFakeInstaller();
    const manifest = generateLatestJson({
      version: "2.0.1-alpha.1",
      installerPath,
      channel: "alpha",
    });
    expect(manifest.channel).toBe("alpha");
  });

  // ── URLs personnalisées ─────────────────────────────────────────

  it("devrait construire les URLs avec owner/repo personnalisés", () => {
    const installerPath = createFakeInstaller();
    const manifest = generateLatestJson({
      version: "1.0.0",
      installerPath,
      owner: "CustomUser",
      repo: "custom-repo",
    });

    expect(manifest.download_url).toBe(
      "https://github.com/CustomUser/custom-repo/releases/download/v1.0.0/NovelTrad-Setup-2.0.1.exe",
    );
    expect(manifest.release_notes_url).toBe(
      "https://github.com/CustomUser/custom-repo/releases/tag/v1.0.0",
    );
  });

  // ── Gestion d'erreurs ───────────────────────────────────────────

  it("devrait lever une erreur si le fichier installer n'existe pas", () => {
    expect(() =>
      generateLatestJson({
        version: "1.0.0",
        installerPath: "/chemin/inexistant/setup.exe",
      }),
    ).toThrow();
  });

  it("devrait générer une date ISO valide (date récente)", () => {
    const installerPath = createFakeInstaller();
    const manifest = generateLatestJson({ version: "1.0.0", installerPath });

    const now = Date.now();
    const manifestDate = new Date(manifest.release_date).getTime();

    // La date du manifeste doit être dans les 10 secondes autour de maintenant
    expect(Math.abs(now - manifestDate)).toBeLessThan(10_000);
  });
});
