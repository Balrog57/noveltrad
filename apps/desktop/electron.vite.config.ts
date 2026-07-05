import { defineConfig, externalizeDepsPlugin } from "electron-vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "node:path";

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, "src/main/index.ts"),
        },
      },
    },
    resolve: {
      alias: {
        "@shared": resolve(__dirname, "../../packages/shared/src"),
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, "src/preload/index.ts"),
        },
        // Force CommonJS output: the preload runs under `sandbox: true`,
        // and Electron's sandboxed preload environment cannot load ESM
        // (https://github.com/electron/electron/issues/41460). With
        // `"type": "module"` in package.json, omitting this would emit
        // `index.mjs` (ESM) which silently fails to execute under sandbox,
        // leaving `window.novelTradAPI` undefined and breaking ALL IPC.
        output: {
          format: "cjs",
          // Explicit `.cjs` extension so the sandbox loader treats it as
          // CommonJS regardless of the package.json `"type": "module"`.
          entryFileNames: "[name].cjs",
        },
      },
    },
  },
  renderer: {
    plugins: [vue()],
    resolve: {
      alias: {
        "@": resolve(__dirname, "src/renderer/src"),
        "@shared": resolve(__dirname, "../../packages/shared/src"),
      },
    },
    root: resolve(__dirname, "src/renderer"),
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, "src/renderer/index.html"),
        },
      },
    },
  },
});
