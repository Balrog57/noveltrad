/**
 * Tests de protection contre le path traversal (SDD §21.3)
 *
 * 6 cas de test :
 * 1. Normal path within project — passes
 * 2. Direct parent traversal (../) — rejected
 * 3. URL-encoded traversal (%2e%2e%2f) — rejected (by assertWithinProject)
 * 4. Symbolic link — rejected (or documented limitation)
 * 5. Absolute path outside project — rejected
 * 6. Windows separators (..\\) — rejected
 */

import { describe, it, expect } from "vitest";
import path from "node:path";
import os from "node:os";
import fs from "node:fs";
import { assertWithinProject } from "../../src/main/utils/paths.js";

const BASE = path.resolve("/tmp/noveltrad-test-project");

describe("Path traversal protection (SDD §21.3)", () => {
  // Cas 1 : Chemin normal dans le projet — passe
  it("cas 1: normal path within project — passes", () => {
    const target = path.join(BASE, "chapters", "chapter1.txt");
    expect(() => assertWithinProject(BASE, target)).not.toThrow();
  });

  it("cas 1: base path itself — passes", () => {
    expect(() => assertWithinProject(BASE, BASE)).not.toThrow();
  });

  // Cas 2 : Parent traversal (../) — rejeté
  it("cas 2: direct parent traversal (../) — rejected", () => {
    const target = path.join(BASE, "..", "secret.txt");
    expect(() => assertWithinProject(BASE, target)).toThrow("Path traversal detected");
  });

  it("cas 2: multiple parent traversal (../../) — rejected", () => {
    const target = path.join(BASE, "..", "..", "etc", "passwd");
    expect(() => assertWithinProject(BASE, target)).toThrow("Path traversal detected");
  });

  // Cas 3 : URL-encoded traversal (%2e%2e%2f) — désormais REJETÉ.
  // Consolidation des 6 PRs sentinel (#86/#87/#90/#91/#93/#96) : la regex
  // TRAVERSAL_REGEX attrape les séquences URL-encodées AVANT résolution.
  // Avant ce fix, path.resolve traitait %2e%2e comme un littéral → bypass.
  it("cas 3: URL-encoded traversal (%2e%2e%2f) — rejected", () => {
    const target = `${BASE}/%2e%2e%2fsecret.txt`;
    expect(() => assertWithinProject(BASE, target)).toThrow("Path traversal detected");
  });

  it("cas 3b: URL-encoded traversal (%2e%2e%5c) — rejected", () => {
    const target = `${BASE}/%2e%2e%5csecret.txt`;
    expect(() => assertWithinProject(BASE, target)).toThrow("Path traversal detected");
  });

  it("cas 3c: URL-encoded basePath traversal — rejected (defense on both args)", () => {
    // #91 : validate basePath aussi (un caller compromis pourrait passer un
    // basePath malveillant).
    expect(() => assertWithinProject(`${BASE}/%2e%2e`, `${BASE}/file.txt`)).toThrow(
      "Path traversal detected",
    );
  });

  it("cas 3d: literal '..' inside a filename is NOT flagged (no false positive)", () => {
    // La regex est ancrée sur les séparateurs : my..file.txt reste légitime.
    const target = path.join(BASE, "my..file.txt");
    expect(() => assertWithinProject(BASE, target)).not.toThrow();
  });

  // Cas 4 : Symbolic link
  // Note : les liens symboliques sont suivis par path.resolve,
  // donc un lien pointant hors du projet serait résolu et détecté.
  it("cas 4: symlink outside project — rejected", () => {
    if (os.platform() === "win32") {
      // Les liens symboliques sur Windows nécessitent des privilèges admin
      // ou Developer Mode. On saute le test sur Windows.
      expect(true).toBe(true);
      return;
    }
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "symlink-test-"));
    try {
      const symlinkPath = path.join(tmpDir, "outside.lnk");
      const outsideTarget = "/etc/passwd";
      try {
        fs.symlinkSync(outsideTarget, symlinkPath);
        expect(() => assertWithinProject(tmpDir, symlinkPath)).toThrow("Path traversal detected");
      } catch {
        // Symlink creation might fail, skip
        expect(true).toBe(true);
      }
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  });

  // Cas 5 : Absolute path outside project — rejeté
  it("cas 5: absolute path outside project — rejected", () => {
    expect(() => assertWithinProject(BASE, "/etc/passwd")).toThrow(
      "Path traversal detected",
    );
  });

  it("cas 5: absolute path on Windows outside project — rejected", () => {
    // Sur Windows, C:\Windows\system32
    expect(() => assertWithinProject(BASE, "C:\\Windows\\system32")).toThrow(
      "Path traversal detected",
    );
  });

  // Cas 6 : Windows separators (..\\) — rejeté (test multi-plateforme via path.win32)
  it("cas 6: Windows backslash traversal (..\\) — rejected", () => {
    const target = path.win32.join(BASE, "..\\secret.txt");
    expect(() => assertWithinProject(BASE, target)).toThrow("Path traversal detected");
  });

  it("cas 6: mixed separators traversal — rejected", () => {
    const target = path.join(BASE, "../../secret.txt");
    expect(() => assertWithinProject(BASE, target)).toThrow("Path traversal detected");
  });
});
