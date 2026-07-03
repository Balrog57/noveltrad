import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock electron-log
vi.mock("electron-log", () => ({
  default: {
    initialize: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    debug: vi.fn(),
    transports: { console: { format: vi.fn() } },
  },
  initialize: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  debug: vi.fn(),
}));

// Mock node:child_process pour contrôler execFile
import { execFile } from "node:child_process";
vi.mock("node:child_process");

import { runEpubcheck, type RunEpubcheckResult } from "../../src/main/services/ExportEngine";

// Mock fs.existsSync pour contrôler la détection d'epubcheck.jar
import fs from "node:fs";
vi.mock("node:fs");

describe("runEpubcheck", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Par défaut, epubcheck.jar n'est pas trouvé
    vi.mocked(fs.existsSync).mockReturnValue(false);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("devrait retourner skipped=true si epubcheck.jar est introuvable", async () => {
    const result = await runEpubcheck("/fake/path.epub");
    expect(result.success).toBe(true);
    expect(result.skipped).toBe(true);
    expect(execFile).not.toHaveBeenCalled();
  });

  it("devrait retourner success=true si epubcheck.jar valide le fichier", async () => {
    // Simuler la présence d'epubcheck.jar via la variable d'environnement
    vi.stubEnv("EPUBCHECK_PATH", "/usr/local/epubcheck/epubcheck.jar");
    vi.mocked(fs.existsSync).mockReturnValue(true);

    // Simuler un appel réussi
    vi.mocked(execFile).mockImplementation((_cmd, _args, _opts, cb: unknown) => {
      const callback = cb as (error: Error | null, stdout: string, stderr: string) => void;
      callback(null, "Validation OK", "");
      return {} as any;
    });

    const result = await runEpubcheck("/some/file.epub");
    expect(result.success).toBe(true);
    expect(result.skipped).toBeUndefined();
    expect(execFile).toHaveBeenCalledWith(
      "java",
      ["-jar", "/usr/local/epubcheck/epubcheck.jar", "/some/file.epub"],
      { timeout: 30000 },
      expect.any(Function),
    );
  });

  it("devrait retourner success=false si epubcheck signale des erreurs", async () => {
    vi.stubEnv("EPUBCHECK_PATH", "/usr/local/epubcheck/epubcheck.jar");
    vi.mocked(fs.existsSync).mockReturnValue(true);

    vi.mocked(execFile).mockImplementation((_cmd, _args, _opts, cb: unknown) => {
      const callback = cb as (error: Error | null, stdout: string, stderr: string) => void;
      callback(new Error("ERROR"), "", "FATAL: missing metadata");
      return {} as any;
    });

    const result = await runEpubcheck("/some/file.epub");
    expect(result.success).toBe(false);
    expect(result.message).toContain("FATAL");
  });

  it("devrait retourner success=false si java n'est pas installé (execFile échoue)", async () => {
    vi.stubEnv("EPUBCHECK_PATH", "/usr/local/epubcheck/epubcheck.jar");
    vi.mocked(fs.existsSync).mockReturnValue(true);

    vi.mocked(execFile).mockImplementation((_cmd, _args, _opts, cb: unknown) => {
      const callback = cb as (error: Error | null, stdout: string, stderr: string) => void;
      callback(new Error("ENOENT: java not found"), "", "");
      return {} as any;
    });

    const result = await runEpubcheck("/some/file.epub");
    expect(result.success).toBe(false);
    expect(result.message).toContain("java not found");
  });
});
