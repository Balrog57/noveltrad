import { app, BrowserWindow, session, globalShortcut, Menu } from "electron";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import { registerIpcRouter } from "./ipc/router.js";
import { getSettingsManager } from "./managers/SettingsManager.js";
import { UpdateManager } from "./managers/UpdateManager.js";
import { logger } from "./utils/logger.js";
import { setUpdateManager } from "./ipc/handlers/update.js";

// P1-4 fix : singleton process-wide partagé avec tous les handlers IPC
// (avant, 12+ instances faisaient chacune des fs.readFileSync synchrones).
const settings = getSettingsManager();
let mainWindow: BrowserWindow | null = null;
let updateManager: UpdateManager | null = null;

function getCrashReportsDir(): string {
  const appData = process.env.APPDATA || path.join(os.homedir(), ".config");
  return path.join(appData, "NovelTrad", "crash-reports");
}

function setupErrorHandlers(): void {
  // SDD §18.4 — Crash reports non récupérées
  process.on("uncaughtException", (error: Error) => {
    const crashDir = getCrashReportsDir();
    fs.mkdirSync(crashDir, { recursive: true });
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const crashFile = path.join(crashDir, `crash-${timestamp}.json`);
    fs.writeFileSync(
      crashFile,
      JSON.stringify(
        {
          timestamp: new Date().toISOString(),
          type: "uncaughtException",
          message: error.message,
          stack: error.stack,
        },
        null,
        2,
      ),
    );
    logger.error("Uncaught exception", error);
  });

  process.on("unhandledRejection", (reason: unknown) => {
    const err = reason instanceof Error ? reason : new Error(String(reason));
    logger.error("Unhandled rejection", err);
  });
}

function setupCspHeaders(): void {
  // SDD §1.1 — Content Security Policy (dev + production)
  const devServerUrl = process.env.VITE_DEV_SERVER_URL;

  const connectSrc = [
    "'self'",
    "http://localhost:11434",
    "https://localhost:11434",
  ];
  if (devServerUrl) {
    // Autoriser le WebSocket du serveur de dev Vite (ws://)
    const devOrigin = new URL(devServerUrl).origin;
    connectSrc.push(devOrigin);
    // Remplacer http/https par ws/wss pour le WebSocket
    connectSrc.push(devOrigin.replace("http", "ws"));
  }

  const csp = [
    "default-src 'self' 'unsafe-inline' data:",
    `connect-src ${connectSrc.join(" ")}`,
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
  ].join("; ");

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        "Content-Security-Policy": [csp],
      },
    });
  });
}

function setupLogForwarding(): void {
  /**
   * SDD §4.12 — Transfert des logs main process vers le renderer.
   * Intercepte console.log/warn/error et les envoie via IPC 'log'.
   * Utilise getMainWindow() pour survivre à un recrément de fenêtre.
   */
  const sendToRenderer = (
    level: "debug" | "info" | "warn" | "error",
    message: string,
  ): void => {
    const win = getMainWindow();
    if (win && !win.isDestroyed()) {
      win.webContents.send("log", {
        level,
        message,
        source: "main",
      });
    }
  };

  const origLog = console.log;
  const origWarn = console.warn;
  const origError = console.error;

  console.log = (...args: unknown[]) => {
    origLog.apply(console, args);
    sendToRenderer("info", args.map(String).join(" "));
  };

  console.warn = (...args: unknown[]) => {
    origWarn.apply(console, args);
    sendToRenderer("warn", args.map(String).join(" "));
  };

  console.error = (...args: unknown[]) => {
    origError.apply(console, args);
    sendToRenderer("error", args.map(String).join(" "));
  };
}

function registerGlobalShortcuts(): void {
  // SDD §4.15 — Keyboard shortcuts
  globalShortcut.register("Control+N", () => {
    const win = getMainWindow();
    if (win && !win.isDestroyed() && win.isFocused()) {
      win.webContents.send("navigate", "/");
    }
  });

  globalShortcut.register("Control+O", () => {
    const win = getMainWindow();
    if (win && !win.isDestroyed() && win.isFocused()) {
      win.webContents.send("menu", "open-project");
    }
  });

  globalShortcut.register("Control+Shift+T", () => {
    const win = getMainWindow();
    if (win && !win.isDestroyed() && win.isFocused()) {
      win.webContents.send("menu", "translate-current");
    }
  });
}

async function createWindow(): Promise<BrowserWindow> {
  setupCspHeaders();

  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      nodeIntegration: false,
      allowRunningInsecureContent: false,
      webSecurity: true,
      // Preload is built as CommonJS (`.cjs`) — see electron.vite.config.ts.
      // Required because `sandbox: true` cannot load an ESM preload
      // (https://github.com/electron/electron/issues/41460).
      preload: path.join(__dirname, "../preload/index.cjs"),
    },
  });

  // Surface any future preload failure in the logs instead of failing silently
  // (this is what masked the ESM/sandbox incompatibility for so long).
  mainWindow.webContents.on("preload-error", (_event, preloadPath, error) => {
    logger.error(
      `[preload-error] Failed to load preload script: ${preloadPath} — ${error.message}`,
      error,
    );
  });

  const devServerUrl = process.env.VITE_DEV_SERVER_URL;
  if (devServerUrl) {
    await mainWindow.loadURL(devServerUrl);
    mainWindow.webContents.openDevTools();
  } else {
    await mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }

  registerGlobalShortcuts();
  setupLogForwarding();

  return mainWindow;
}

function getMainWindow(): BrowserWindow | null {
  return mainWindow;
}

setupErrorHandlers();

app.whenReady().then(async () => {
  logger.info("NovelTrad starting...");

  // Native menu with Help (SDD §4.15)
  const menu = Menu.buildFromTemplate([
    {
      label: "Fichier",
      submenu: [
        { label: "Nouveau projet", accelerator: "CmdOrCtrl+N", click: () => {
          const win = getMainWindow();
          if (win && !win.isDestroyed()) {win.webContents.send("navigate", "/");}
        }},
        { label: "Ouvrir un projet", accelerator: "CmdOrCtrl+O", click: () => {
          const win = getMainWindow();
          if (win && !win.isDestroyed()) {win.webContents.send("menu", "open-project");}
        }},
        { type: "separator" },
        { role: "quit", label: "Quitter" },
      ],
    },
    {
      label: "Aide",
      submenu: [
        { label: "Guide d'utilisation", click: () => {
          const win = getMainWindow();
          if (win && !win.isDestroyed()) {win.webContents.send("navigate", "/help");}
        }},
        { label: "GitHub", click: async () => { const { shell } = await import("electron"); await shell.openExternal("https://github.com/Balrog57/noveltrad"); } },
      ],
    },
  ]);
  Menu.setApplicationMenu(menu);

  await registerIpcRouter();
  await createWindow();

  updateManager = new UpdateManager(
    settings.get("updateChannel"),
    getMainWindow,
  );
  // Partager l'instance unique avec les handlers IPC (évite la double émission
  // d'events qui ouvrait des dialogues en double)
  setUpdateManager(updateManager);
  // Vérification immédiate au démarrage + notification toast
  setTimeout(() => {
    updateManager?.check().catch((err) => {
      logger.warn("Initial update check failed", err);
    });
  }, 5_000);

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});
