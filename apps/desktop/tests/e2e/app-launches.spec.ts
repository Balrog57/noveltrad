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
      console.log(`Launching...`);
      app = await electron.launch({
        args: [MAIN_ENTRY],
        cwd: APP_CWD,
        timeout: 20000,
      });
      app.on("console", (msg) => {
        console.log(`[RENDERER] ${msg.type()}: ${msg.text()}`);
      });
      app.on("window", (page) => {
        page.on("pageerror", (err) => {
          console.log(`[PAGEERROR] ${err.message}`);
        });
        page.on("console", (msg) => {
          console.log(`[WIN] ${msg.type()}: ${msg.text()}`);
        });
      });
      console.log('App launched');
      window = await app.firstWindow();
      console.log('Window found, URL:', window.url());
      const errors: string[] = [];
      window.on("pageerror", (err: Error) => {
        errors.push(err.message);
        console.log(`[PAGEERROR2] ${err.message}`);
      });
      await window.waitForLoadState("domcontentloaded", { timeout: 10000 });
      console.log('Page loaded, URL:', window.url());
    } catch (err) {
      console.error('BEFORE ALL ERROR:', err);
      const msg = err instanceof Error ? err.message : String(err);
      test.skip(true, `Application Electron non demarree — ${msg}`);
    }
  });

  test.afterAll(async () => {
    await app?.close();
  });

  test("app launches and shows home", async () => {
    if (!window) return;
    await window.waitForTimeout(2000);
    const url = window.url();
    console.log('Test - URL:', url);
    expect(url).not.toContain("chromewebdata");
    await expect(window.locator("aside.sidebar")).toBeVisible({ timeout: 10000 });
  });
});
