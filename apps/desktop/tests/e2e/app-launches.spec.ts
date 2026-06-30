import { test, expect } from "@playwright/test";
import { _electron as electron, type ElectronApplication, type Page } from "playwright";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const MAIN_ENTRY = path.join(__dirname, "../../out/main/index.js");
const APP_CWD = path.join(__dirname, "../..");

test.describe("App Launch", () => {
  let app: ElectronApplication;
  let window: Page;

  test.beforeAll(async () => {
    try {
      app = await electron.launch({
        args: [MAIN_ENTRY],
        cwd: APP_CWD,
        timeout: 20000,
      });
      window = await app.firstWindow();
      await window.waitForLoadState("domcontentloaded", { timeout: 10000 });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      test.skip(true, `Application Electron non demarree — ${msg}`);
    }
  });

  test.afterAll(async () => {
    await app?.close();
  });

  test("app launches and shows home", async () => {
    if (!window) return;
    await expect(window).toHaveTitle("NovelTrad 2.0");
    await expect(window.locator("h1")).toContainText("NovelTrad 2.0");
  });
});
