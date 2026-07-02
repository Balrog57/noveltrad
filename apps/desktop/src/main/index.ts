import { app, BrowserWindow, session, globalShortcut } from "electron";
import path from "node:path";
import fs from "node:fs";
import os from "node:os";
import { registerIpcRouter } from "./ipc/router.js";
import { SettingsManager } from "./managers/SettingsManager.js";
import { UpdateManager } from "./managers/UpdateManager.js";
import { logger } from "./utils/logger.js";
import { PluginHost } from "./plugins/PluginHost.js";
import { setPluginHost, setSettingsManager } from "./ipc/handlers/plugins.js";
import { AiRouter } from "./services/AiRouter.js";
import { LexiconEngine } from "./services/LexiconEngine.js";
import { ExportEngine } from "./services/ExportEngine.js";

const settings = new SettingsManager();
let mainWindow: BrowserWindow | null = null;
let updateManager: UpdateManager | null = null;
let pluginHost: PluginHost | null = null;

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
  // Désactivé en mode production pour éviter les conflits avec le protocole file://
  if (!process.env.VITE_DEV_SERVER_URL) return;

  // SDD §1.1 — Content Security Policy (dev mode only)
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
    "default-src 'self'",
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
   */
  const sendToRenderer = (
    level: "debug" | "info" | "warn" | "error",
    message: string,
  ): void => {
    const win = mainWindow;
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
    if (mainWindow?.isFocused()) {
      mainWindow.webContents.send("navigate", "/");
    }
  });

  globalShortcut.register("Control+O", () => {
    if (mainWindow?.isFocused()) {
      mainWindow.webContents.send("menu", "open-project");
    }
  });

  globalShortcut.register("Control+Shift+T", () => {
    if (mainWindow?.isFocused()) {
      mainWindow.webContents.send("menu", "translate-current");
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
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
      allowRunningInsecureContent: false,
      webSecurity: true,
      preload: path.join(__dirname, "../preload/index.mjs"),
    },
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
  registerIpcRouter();
  await createWindow();

  // SDD §15 : initialisation du PluginHost
  const aiRouter = new AiRouter();
  const lexiconEngine = new LexiconEngine();
  const exportEngine = new ExportEngine();
  pluginHost = new PluginHost(
    {
      aiRouter,
      lexiconEngine,
      logger,
    },
    exportEngine,
  );

  // Connecter le PluginHost aux handlers IPC
  setPluginHost(pluginHost);
  setSettingsManager(settings);

  // Découvrir et charger les plugins activés (flux permissions différé)
  const enabledPluginIds = settings.get("enabledPlugins");
  const sensitivePlugins = await pluginHost.init(enabledPluginIds);

  // Si des plugins sensibles sont en attente, demander confirmation à l'utilisateur
  if (sensitivePlugins.length > 0) {
    mainWindow?.webContents.once("did-finish-load", async () => {
      mainWindow?.webContents.send("plugin:request-permissions");
    });
  }

  updateManager = new UpdateManager(
    settings.get("updateChannel"),
    getMainWindow,
  );
  setTimeout(() => {
    updateManager?.check().catch((err) => {
      logger.warn("Initial update check failed", err);
    });
  }, 30_000);

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
