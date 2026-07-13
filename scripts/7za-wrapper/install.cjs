#!/usr/bin/env node
/**
 * Post-install : installe le wrapper 7za.exe qui masque l'exit code 2 de 7-Zip.
 *
 * Contexte (Windows non-admin, Mode développeur désactivé) :
 *   electron-builder télécharge winCodeSign-2.6.0.7z puis l'extrait avec 7za.
 *   Cette archive contient 2 liens symboliques macOS (libcrypto.dylib,
 *   libssl.dylib) que 7za ne peut pas créer sans le privilège "Créer des
 *   liens symboliques". 7za sort alors en code 2 (warning), que le binaire Go
 *   `app-builder` d'electron-builder traite comme fatal → le build Windows
 *   échoue systématiquement.
 *
 *   Comme les builds NovelTrad sont non signés, ces symlinks macOS sont
 *   inutiles. Le wrapper délègue au vrai 7za et masque le code de sortie 2.
 *
 * Effet :
 *   - Renomme `node_modules/7zip-bin/win/x64/7za.exe` → `7za-real.exe`
 *   - Copie le wrapper précompilé à la place de `7za.exe`
 *
 * Idempotent : peut être relancé sans effet secondaire. No-op sur non-Windows
 * ou si 7zip-bin n'est pas installé. Le wrapper se recompile si Go est dispo
 * et que la taille du binaire embarqué ne correspond pas (rebuild maison).
 */
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const SEVENZIP_DIR = path.join(
  REPO_ROOT,
  "node_modules",
  "7zip-bin",
  "win",
  "x64",
);
const REAL_EXE = path.join(SEVENZIP_DIR, "7za-real.exe");
const WRAPPER_EXE = path.join(SEVENZIP_DIR, "7za.exe");
const BUNDLED_WRAPPER = path.join(__dirname, "bin", "7za-wrapper-x64.exe");

function log(msg) {
  console.log(`[7za-wrapper] ${msg}`);
}

function main() {
  // No-op hors Windows.
  if (process.platform !== "win32") {
    log("skip (non-Windows)");
    return;
  }

  // No-op si 7zip-bin n'est pas installé (dépendance pas encore posée).
  if (!fs.existsSync(SEVENZIP_DIR)) {
    log(`skip (7zip-bin absent : ${SEVENZIP_DIR})`);
    return;
  }

  // No-op si le wrapper précompilé embarqué est absent (repo incomplet).
  if (!fs.existsSync(BUNDLED_WRAPPER)) {
    log(`ERREUR : wrapper précompilé absent (${BUNDLED_WRAPPER})`);
    process.exit(1);
  }

  const BUNDLED_SIZE = fs.statSync(BUNDLED_WRAPPER).size;

  // Cas 1 : le wrapper est déjà en place (taille identique) → idempotent.
  if (fs.existsSync(WRAPPER_EXE) && fs.existsSync(REAL_EXE)) {
    const currentSize = fs.statSync(WRAPPER_EXE).size;
    if (currentSize === BUNDLED_SIZE) {
      log("déjà en place (wrapper présent) ✓");
      return;
    }
    // 7za.exe existe mais n'est pas le wrapper (taille différente) et
    // 7za-real.exe aussi → état incohérent, on écrase juste le wrapper.
    fs.copyFileSync(BUNDLED_WRAPPER, WRAPPER_EXE);
    log(`wrapper réinstallé ✓ (${WRAPPER_EXE})`);
    return;
  }

  // Cas 2 : 7za.exe existe mais pas 7za-real.exe → première install propre.
  // Le vrai binaire npm est en place, on le renomme puis on pose le wrapper.
  if (fs.existsSync(WRAPPER_EXE) && !fs.existsSync(REAL_EXE)) {
    // Vérifier que ce n'est pas déjà notre wrapper.
    const currentSize = fs.statSync(WRAPPER_EXE).size;
    if (currentSize === BUNDLED_SIZE) {
      log("déjà en place (wrapper présent, 7za-real manquant) ✓");
      return;
    }
    fs.renameSync(WRAPPER_EXE, REAL_EXE);
    log(`renommé 7za.exe → 7za-real.exe`);
    fs.copyFileSync(BUNDLED_WRAPPER, WRAPPER_EXE);
    log(`wrapper installé ✓ (${WRAPPER_EXE})`);
    return;
  }

  // Cas 3 : ni 7za.exe ni 7za-real.exe → install cassée.
  if (!fs.existsSync(WRAPPER_EXE) && !fs.existsSync(REAL_EXE)) {
    log("aucun 7za.exe trouvé, abandon");
    return;
  }

  // Cas 4 : seul 7za-real.exe existe (7za.exe manquant) → on repose le wrapper.
  fs.copyFileSync(BUNDLED_WRAPPER, WRAPPER_EXE);
  log(`wrapper installé ✓ (${WRAPPER_EXE})`);
}

try {
  main();
} catch (err) {
  console.error(`[7za-wrapper] ERREUR : ${err && err.stack ? err.stack : err}`);
  process.exit(1);
}
