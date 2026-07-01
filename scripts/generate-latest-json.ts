#!/usr/bin/env node
/**
 * generate-latest-json.ts
 * Génère le manifeste latest.json pour l'auto-update (SDD §17.5).
 *
 * Usage:
 *   npx tsx scripts/generate-latest-json.ts \
 *     --version 2.0.1 \
 *     --installer ./dist/NovelTrad-Setup-2.0.1.exe \
 *     --output ./dist/latest.json \
 *     [--channel stable|beta|alpha] \
 *     [--owner Balrog57] \
 *     [--repo noveltrad]
 */

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { basename } from "node:path";
import { fileURLToPath } from "node:url";

// ── Types ─────────────────────────────────────────────────────────

export interface LatestManifest {
  version: string;
  channel: "stable" | "beta" | "alpha";
  release_date: string;
  download_url: string;
  sha256: string;
  release_notes_url: string;
  mandatory: boolean;
  min_app_version: string;
}

export interface GenerateOptions {
  version: string;
  installerPath: string;
  channel?: "stable" | "beta" | "alpha";
  owner?: string;
  repo?: string;
}

// ── Core logic ────────────────────────────────────────────────────

export function generateLatestJson(options: GenerateOptions): LatestManifest {
  const {
    version,
    installerPath,
    channel = "stable",
    owner = "Balrog57",
    repo = "noveltrad",
  } = options;

  // SHA256 du fichier installer
  const installerBuffer = readFileSync(installerPath);
  const sha256 = createHash("sha256")
    .update(installerBuffer)
    .digest("hex");

  // Construction des URLs
  const tag = `v${version}`;
  const installerName = basename(installerPath);
  const downloadUrl = `https://github.com/${owner}/${repo}/releases/download/${tag}/${installerName}`;
  const releaseNotesUrl = `https://github.com/${owner}/${repo}/releases/tag/${tag}`;

  return {
    version,
    channel: channel as "stable" | "beta" | "alpha",
    release_date: new Date().toISOString(),
    download_url: downloadUrl,
    sha256,
    release_notes_url: releaseNotesUrl,
    mandatory: false,
    min_app_version: "1.0.0",
  };
}

// ── CLI entry point ───────────────────────────────────────────────

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);

  const getArg = (flag: string): string | undefined => {
    const idx = args.indexOf(flag);
    return idx !== -1 ? args[idx + 1] : undefined;
  };

  const version = getArg("--version");
  const installerPath = getArg("--installer");
  const outputPath = getArg("--output");
  const channel = getArg("--channel") ?? "stable";
  const owner = getArg("--owner") ?? "Balrog57";
  const repo = getArg("--repo") ?? "noveltrad";

  if (!version || !installerPath || !outputPath) {
    console.error(
      "Usage: npx tsx scripts/generate-latest-json.ts \\\n" +
        "  --version <version> \\\n" +
        "  --installer <path> \\\n" +
        "  --output <path> \\\n" +
        "  [--channel stable|beta|alpha] \\\n" +
        "  [--owner <owner>] \\\n" +
        "  [--repo <repo>]",
    );
    process.exit(1);
  }

  const manifest = generateLatestJson({
    version,
    installerPath,
    channel: channel as "stable" | "beta" | "alpha",
    owner,
    repo,
  });

  writeFileSync(outputPath, JSON.stringify(manifest, null, 2));
  console.log(`✅ latest.json generated → ${outputPath}`);
}
