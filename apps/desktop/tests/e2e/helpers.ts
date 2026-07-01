import type { Page } from "playwright";

/**
 * Ferme le wizard de premier lancement s'il est présent.
 * Appeler après `waitForLoadState`.
 */
export async function dismissWizard(window: Page): Promise<void> {
  const wizardOverlay = window.locator(".wizard-overlay");
  try {
    await wizardOverlay.waitFor({ state: "visible", timeout: 3000 });
    // Cliquer "Passer" pour sauter à la dernière étape
    const skipBtn = wizardOverlay.locator("button.btn-ghost");
    if (await skipBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await skipBtn.click();
      await window.waitForTimeout(500);
    }
    // Cliquer le bouton principal (Commencer) pour fermer le wizard
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
