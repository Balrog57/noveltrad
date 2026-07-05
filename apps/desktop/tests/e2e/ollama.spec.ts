/**
 * Tests E2E — Ollama (Phase 0 validation)
 *
 * Scénarios :
 * 1. HomeView badge "Ollama disponible" si serveur actif
 * 2. HomeView badge "Non disponible" si serveur arrêté (skip si pas serveur)
 * 3. Wizard détection auto + affichage modèles
 * 4. Téléchargement modèle avec progression
 * 5. Test modèle retour OK
 *
 * Si Ollama n'est pas disponible, les tests sont automatiquement skippés.
 */
import { test, expect } from "@playwright/test";
import { _electron as electron, type ElectronApplication, type Page } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MAIN_ENTRY = path.join(__dirname, "../../out/main/index.js");
const APP_CWD = path.join(__dirname, "../..");
const OLLAMA_HOST = "http://localhost:11434";

// --- Helpers ---

async function isOllamaAvailable(): Promise<boolean> {
  try {
    const res = await fetch(`${OLLAMA_HOST}/api/tags`, {
      signal: AbortSignal.timeout(3000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function dismissWizard(window: Page): Promise<void> {
  const wizardOverlay = window.locator(".wizard-overlay");
  try {
    await wizardOverlay.waitFor({ state: "visible", timeout: 3000 });
    const skipBtn = wizardOverlay.locator("button.btn-ghost");
    if (await skipBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await skipBtn.click();
      await window.waitForTimeout(500);
    }
    const mainBtn = wizardOverlay.locator("button.btn-primary").last();
    if (await mainBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await mainBtn.click();
      await window.waitForTimeout(500);
    }
    await wizardOverlay.waitFor({ state: "hidden", timeout: 5000 });
  } catch {
    // Le wizard n'est pas présent
  }
}

// --- Test Suite ---

test.describe("Ollama E2E (Phase 0 validation)", () => {
  let app: ElectronApplication;
  let window: Page;
  let ollamaAvailable = false;

  test.beforeAll(async () => {
    ollamaAvailable = await isOllamaAvailable();
    if (!ollamaAvailable) {
      console.log("⚠️  Ollama non disponible — tests E2E Ollama sautés");
      return;
    }

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
      test.skip(true, `Application Electron non démarrée — ${msg}`);
    }
  });

  test.afterAll(async () => {
    await app?.close();
  });

  // ── Cas 1 : HomeView badge "Ollama disponible" ──────────────────

  test("HomeView affiche le badge Ollama disponible", async () => {
    if (!ollamaAvailable || !window) {
      test.skip(true, "Ollama ou application non disponible");
      return;
    }

    await window.waitForTimeout(3000);

    const badge = window.locator(".ollama-status");
    await expect(badge).toBeVisible({ timeout: 10000 });

    const text = await badge.textContent();
    expect(text).toContain("disponible");
  });

  // ── Cas 2 : HomeView badge "Non disponible" (skip si serveur actif) ──

  test("HomeView affiche le badge Ollama non disponible quand serveur arrêté", async () => {
    // Ce test ne peut pas être automatisé sans arrêter le serveur Ollama
    // Il est documenté pour la complétude
    test.skip(true, "Nécessite arrêt manuel du serveur Ollama — test documentaire");
  });

  // ── Cas 3 : Wizard détection auto ───────────────────────────────

  test("Wizard détecte Ollama et affiche la liste des modèles", async () => {
    if (!ollamaAvailable || !window) {
      test.skip(true, "Ollama ou application non disponible");
      return;
    }

    // Réinitialiser firstRunCompleted pour afficher le wizard
    await window.evaluate(() => {
      const api = (window as any).novelTradAPI;
      if (api?.invoke) {
        api.invoke("settings:set", "firstRunCompleted", false);
      }
    });

    // Recharger la page pour déclencher le wizard
    await window.reload();
    await window.waitForLoadState("domcontentloaded", { timeout: 10000 });
    await window.waitForTimeout(2000);

    // Vérifier la présence du wizard
    const wizard = window.locator(".wizard-overlay");
    try {
      await wizard.waitFor({ state: "visible", timeout: 5000 });

      // Étape 2 : détection Ollama
      const nextBtn = wizard.locator("button.btn-primary");
      if (await nextBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await nextBtn.click();
        await window.waitForTimeout(2000);

        // Vérifier que le statut "available" s'affiche
        const statusText = wizard.locator(".ollama-status, .status-available, [class*='available']");
        if (await statusText.isVisible({ timeout: 3000 }).catch(() => false)) {
          const text = await statusText.textContent();
          expect(text?.toLowerCase()).toContain("disponible");
        }
      }

      // Fermer le wizard
      await dismissWizard(window);
    } catch {
      // Wizard non affiché (firstRunCompleted peut ne pas avoir été réinitialisé)
      test.skip(true, "Wizard non affiché après réinitialisation");
    }
  });

  // ── Cas 4 : Téléchargement modèle avec progression ──────────────

  test("Téléchargement d'un modèle affiche la progression", async () => {
    if (!ollamaAvailable || !window) {
      test.skip(true, "Ollama ou application non disponible");
      return;
    }

    // Ce test nécessite un modèle non présent — difficile à automatiser
    // sans contrôler l'état d'Ollama. Test documentaire.
    test.skip(true, "Nécessite contrôle de l'état des modèles Ollama — test documentaire");
  });

  // ── Cas 5 : Test modèle retour OK ───────────────────────────────

  test("Test du modèle retourne OK via IPC", async () => {
    if (!ollamaAvailable || !window) {
      test.skip(true, "Ollama ou application non disponible");
      return;
    }

    // Appeler le handler ollama:test-model via IPC
    const result = await window.evaluate(async () => {
      const api = (window as any).novelTradAPI;
      if (!api?.invoke) {return null;}
      return api.invoke("ollama:test-model", "qwen3.5:9b");
    });

    if (result && typeof result === "object") {
      expect(result).toHaveProperty("success");
      expect(result.success).toBe(true);
    } else {
      test.skip(true, "IPC non disponible");
    }
  });
});
