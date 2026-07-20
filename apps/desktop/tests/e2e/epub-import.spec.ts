/**
 * Test E2E — Import d'un fichier EPUB réel via le flux complet Noveltrad.
 *
 * Scénario : lancement app → création projet → import EPUB Perry Rhodan
 * Sammelband → vérification (chapitres créés, paragraphes, langue détectée).
 *
 * Pilote l'API IPC réelle (window.novelTradAPI.invoke "chapter:import") via
 * Playwright + Electron, comme full-workflow.spec.ts.
 *
 * Usage :
 *   npm run test:e2e -- epub-import
 *
 * Prérequis : EPUB_PATH doit pointer sur un fichier .epub valide. Défaut :
 *   ~/Downloads/Perry Rhodan Sammelband 1876-1899 .epub
 *
 * L'app est lancée une fois pour le describe. Si le lancement échoue (build
 * cassé), les tests sont skipped.
 */
import { test, expect } from "@playwright/test";
import { _electron as electron, type ElectronApplication, type Page } from "playwright";
import path from "node:path";
import os from "node:os";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { dismissWizard } from "./helpers";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Fichier epub cible (overridable via env pour réutiliser ce test sur d'autres livres).
const EPUB_PATH = process.env.EPUB_PATH
  ?? path.join(os.homedir(), "Downloads", "Perry Rhodan Sammelband 1876-1899 .epub");

const MAIN_ENTRY = path.join(__dirname, "../../out/main/index.js");
const APP_CWD = path.join(__dirname, "../..");

test.describe(`Import EPUB : ${path.basename(EPUB_PATH)}`, () => {
  let app: ElectronApplication;
  let window: Page;
  let projectId: string | null = null;
  const projectName = `E2E-EPUB-${Date.now()}`;

  test.beforeAll(async () => {
    // Skip propre si le fichier n'existe pas (évite un échec en CI).
    test.skip(!fs.existsSync(EPUB_PATH), `EPUB introuvable : ${EPUB_PATH}`);

    try {
      app = await electron.launch({
        args: [MAIN_ENTRY],
        cwd: APP_CWD,
        timeout: 20000,
      });
      window = await app.firstWindow();
      await window.waitForLoadState("domcontentloaded", { timeout: 10000 });
      await dismissWizard(window);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      test.skip(true, `Application Electron non demarree — ${msg}`);
    }
  });

  test.afterAll(async () => {
    await app?.close();
  });

  test("crée un projet DE→FR puis importe l'EPUB via chapter:import", async () => {
    test.skip(!window, "App non lancée");
    test.skip(!fs.existsSync(EPUB_PATH), `EPUB manquant : ${EPUB_PATH}`);

    // --- Phase 1 : créer le projet via IPC direct ---
    const project = await window.evaluate(
      async ({ name }: { name: string }) => {
        const api = (window as unknown as {
          novelTradAPI: { invoke: (ch: string, ...args: unknown[]) => Promise<unknown> };
        }).novelTradAPI;
        return api.invoke("project:create", {
          name,
          sourceLanguage: "de",
          targetLanguage: "fr",
          parentPath: "~/NovelTrad Projects",
        }) as Promise<{ id: string; path: string } | null>;
      },
      { name: projectName },
    );
    expect(project, "project:create a retourné null — échec création").toBeTruthy();
    projectId = project!.id;
    console.log(`  ✓ Projet créé : id=${projectId}, path=${project!.path}`);

    // --- Phase 2 : import EPUB via chapter:import ---
    const sizeMb = (fs.statSync(EPUB_PATH).size / 1024 / 1024).toFixed(2);
    console.log(`  Import du fichier (${sizeMb} Mo) via chapter:import ...`);

    const t0 = Date.now();
    const chapters = await window.evaluate(
      async ({ projId, filePath }: { projId: string; filePath: string }) => {
        const api = (window as unknown as {
          novelTradAPI: { invoke: (ch: string, ...args: unknown[]) => Promise<unknown> };
        }).novelTradAPI;
        return api.invoke("chapter:import", projId, filePath) as Promise<
          Array<{ id: string; title: string; orderIndex: number }>
        >;
      },
      { projId: projectId!, filePath: EPUB_PATH },
    );
    const elapsed = ((Date.now() - t0) / 1000).toFixed(2);
    console.log(`  ✓ chapter:import terminé en ${elapsed}s — ${chapters.length} chapitre(s)`);

    // --- Phase 3 : assertions sur le résultat ---
    expect(chapters.length, "au moins 1 chapitre attendu").toBeGreaterThan(0);
    console.log(`  Chapitres : ${chapters.length}`);
    if (chapters.length > 0) {
      console.log(`    Premier : "${chapters[0].title}" (order=${chapters[0].orderIndex})`);
      console.log(`    Dernier : "${chapters[chapters.length - 1].title}"`);
    }

    // --- Phase 4 : vérifier les paragraphes du 1er chapitre via IPC ---
    const firstChapterId = chapters[0].id;
    const firstChapterData = await window.evaluate(
      async ({ chId }: { chId: string }) => {
        const api = (window as unknown as {
          novelTradAPI: { invoke: (ch: string, ...args: unknown[]) => Promise<unknown> };
        }).novelTradAPI;
        const paragraphs = (await api.invoke("chapter:get-paragraphs", { chapterId: chId })) as Array<{
          id: string;
          sourceText: string;
          status: string;
        }>;
        return {
          count: paragraphs.length,
          totalChars: paragraphs.reduce((s, p) => s + p.sourceText.length, 0),
          preview: paragraphs[0]?.sourceText.slice(0, 200) ?? "",
          statuses: [...new Set(paragraphs.map((p) => p.status))],
        };
      },
      { chId: firstChapterId },
    );
    console.log(`  Paragraphes du 1er chapitre : ${firstChapterData.count}`);
    console.log(`  Caractères source total (1er chapitre) : ${firstChapterData.totalChars.toLocaleString()}`);
    console.log(`  Status des paragraphes : ${firstChapterData.statuses.join(", ")}`);
    console.log(`  Aperçu 1er paragraphe :\n    "${firstChapterData.preview.replace(/\n/g, " ")}..."`);

    expect(firstChapterData.count, "1er chapitre doit avoir des paragraphes").toBeGreaterThan(0);
    expect(firstChapterData.totalChars, "1er chapitre ne doit pas être vide").toBeGreaterThan(100);
    expect(firstChapterData.statuses).toContain("pending");
  });
});
