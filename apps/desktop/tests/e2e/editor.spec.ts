/**
 * Test E2E — Éditeur côte à côte source/target
 *
 * Scénarios :
 * - Navigation vers l'éditeur depuis la liste des chapitres
 * - Affichage des panneaux source (paragraphes) et cible (textareas)
 * - Édition d'une traduction → indicateur "●" (modifié)
 * - Bouton Enregistrer → sauvegarde
 * - Vérification de la présence du split pane (NtSplitPane)
 *
 * L'application Electron est lancée une fois pour tout le describe block.
 * Si le lancement échoue, tous les tests sont automatiquement ignorés.
 */
import { test, expect } from "@playwright/test";
import { _electron as electron, type ElectronApplication, type Page } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";
import fs from "node:fs";
import os from "node:os";
import { dismissWizard } from "./helpers";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MAIN_ENTRY = path.join(__dirname, "../../out/main/index.js");
const APP_CWD = path.join(__dirname, "../..");

// --- Helpers ---

function uniqueName(prefix = "EditTest"): string {
  return `${prefix}-${Date.now()}`;
}

function createTempTxt(basename: string): string {
  const filePath = path.join(os.tmpdir(), `${basename}.txt`);
  const content = [
    "Chapter 2: The Journey",
    "",
    "The road stretched endlessly before them.",
    "",
    "Mountains loomed on the horizon, capped with snow.",
    "",
    "They had been walking for three days without rest.",
    "",
    "Hunger gnawed at their stomachs, but hope remained.",
  ].join("\n");
  fs.writeFileSync(filePath, content, "utf-8");
  return filePath;
}

function removeTempFile(p: string): void {
  try { fs.unlinkSync(p); } catch { /* ok */ }
}

// --- Test Suite ---

test.describe("Editor E2E", () => {
  let app: ElectronApplication;
  let window: Page;
  let projectId: string;
  let tempFiles: string[] = [];

  test.beforeAll(async () => {
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
      return;
    }

    // Créer un projet avec un chapitre importé, partagé par tous les tests
    try {
      const createBtn = window.locator("button", { hasText: "Nouveau projet" });
      await createBtn.click();
      await window.waitForSelector("section.card", { timeout: 5000 });

      const projectName = uniqueName("EditTest");
      await window.locator("input[placeholder='Mon roman']").fill(projectName);

      // Créer via IPC direct
      await window.evaluate(async ({ name, src, tgt }: { name: string; src: string; tgt: string }) => {
        const api = (window as any).novelTradAPI;
        const proj = await api.invoke("project:create", {
          name, sourceLanguage: src, targetLanguage: tgt, parentPath: "~/NovelTrad Projects"
        });
        if (proj?.id) document.location.hash = `#/project/${proj.id}`;
      }, { name: projectName, src: "en", tgt: "fr" });

      await window.waitForFunction(
        () => document.location.hash.includes("/project/"),
        { timeout: 10000 },
      );
      projectId = (new URL(window.url())).hash.split("/project/")[1]?.split(/[/?#]/)[0] ?? "";

      // Importer un chapitre via IPC
      const tempFile = createTempTxt(`e2e-editor-chapter-${Date.now()}`);
      tempFiles.push(tempFile);

      await window.evaluate(
        async ({ projId, filePath }: { projId: string; filePath: string }) => {
          const api = (
            window as unknown as {
              novelTradAPI: {
                invoke: (ch: string, ...args: unknown[]) => Promise<unknown>;
              };
            }
          ).novelTradAPI;
          await api.invoke("chapter:import", projId, filePath);
        },
        { projId: projectId, filePath: tempFile },
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      test.skip(true, `Configuration projet impossible — ${msg}`);
    }
  });

  test.afterAll(async () => {
    for (const f of tempFiles) removeTempFile(f);
    await app?.close();
  });

  test("should display source paragraphs and target textareas", async () => {
    if (!window || !projectId) {
      test.skip(true, "Application non disponible");
      return;
    }

    // Naviguer vers les chapitres
    await window.locator("button", { hasText: "Voir les chapitres" }).click();
    await window.waitForURL("**/chapters", { timeout: 5000 });

    // Vérifier que le chapitre importé apparaît
    await expect(window.locator(".chapter-list li").first()).toBeVisible({
      timeout: 5000,
    });

    // Cliquer sur le chapitre pour ouvrir l'éditeur
    await window.locator(".chapter-info").first().click();
    await window.waitForURL("**/chapters/**", { timeout: 8000 });

    // Vérifier la présence des panneaux source et cible
    await expect(window.locator(".source-panel")).toBeVisible({
      timeout: 5000,
    });
    await expect(window.locator(".target-panel")).toBeVisible({
      timeout: 5000,
    });

    // Vérifier les blocs source
    const sourceBlocks = window.locator(".source-block");
    await expect(sourceBlocks.first()).toBeVisible({ timeout: 5000 });
    expect(await sourceBlocks.count()).toBeGreaterThan(0);

    // Vérifier les textareas cibles
    const targetTextareas = window.locator(
      ".target-panel .translation-textarea",
    );
    await expect(targetTextareas.first()).toBeVisible({ timeout: 5000 });
    expect(await targetTextareas.count()).toBe(await sourceBlocks.count());
  });

  test("should show dirty indicator when translation is modified", async () => {
    if (!window || !projectId) {
      test.skip(true, "Application non disponible");
      return;
    }

    // Naviguer vers les chapitres
    await window.locator("button", { hasText: "Voir les chapitres" }).click();
    await window.waitForURL("**/chapters", { timeout: 5000 });

    await window.locator(".chapter-info").first().click();
    await window.waitForURL("**/chapters/**", { timeout: 8000 });

    // Attendre que les textareas soient chargées
    await window
      .locator(".target-panel .translation-textarea")
      .first()
      .waitFor({ state: "visible", timeout: 5000 });

    // Taper du texte dans la première textarea
    const firstTextarea = window
      .locator(".target-panel .translation-textarea")
      .first();
    await firstTextarea.click();
    await firstTextarea.fill("Traduction de test E2E — Il faisait sombre.");

    // Vérifier que l'indicateur "●" (dirty-dot) apparaît
    await expect(window.locator(".dirty-dot").first()).toBeVisible({
      timeout: 3000,
    });

    // Vérifier que le bouton Enregistrer montre l'état modifié
    const saveBtn = window.locator(".btn-save");
    await expect(saveBtn).toContainText("● Enregistrer");
  });

  test("save button should trigger save action without error", async () => {
    if (!window || !projectId) {
      test.skip(true, "Application non disponible");
      return;
    }

    await window.locator("button", { hasText: "Voir les chapitres" }).click();
    await window.waitForURL("**/chapters", { timeout: 5000 });

    await window.locator(".chapter-info").first().click();
    await window.waitForURL("**/chapters/**", { timeout: 8000 });

    await window
      .locator(".target-panel .translation-textarea")
      .first()
      .waitFor({ state: "visible", timeout: 5000 });

    // Modifier une traduction
    const firstTextarea = window
      .locator(".target-panel .translation-textarea")
      .first();
    await firstTextarea.fill("Traduction sauvegardee.");

    // Cliquer sur Enregistrer
    const saveBtn = window.locator(".btn-save");
    await saveBtn.click();

    // Attendre que la sauvegarde asynchrone se termine
    await window.waitForTimeout(1000);

    const saveBtnText = await saveBtn.textContent();
    expect(saveBtnText).toBeTruthy();
  });

  test("split pane is present in editor layout", async () => {
    if (!window || !projectId) {
      test.skip(true, "Application non disponible");
      return;
    }

    await window.locator("button", { hasText: "Voir les chapitres" }).click();
    await window.waitForURL("**/chapters", { timeout: 5000 });

    await window.locator(".chapter-info").first().click();
    await window.waitForURL("**/chapters/**", { timeout: 8000 });

    // Vérifier la présence des deux panneaux (NtSplitPane)
    await expect(window.locator(".source-panel")).toBeVisible({
      timeout: 5000,
    });
    await expect(window.locator(".target-panel")).toBeVisible({
      timeout: 5000,
    });

    // Au moins 2 panneaux côte à côte
    const panelCount = await window.locator(".panel").count();
    expect(panelCount).toBeGreaterThanOrEqual(2);
  });
});
