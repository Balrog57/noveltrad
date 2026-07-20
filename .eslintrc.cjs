/**
 * ESLint configuration for NovelTrad.
 *
 * TypeScript + Vue support via @typescript-eslint/parser and eslint-plugin-vue.
 */

// eslint-disable-next-line no-undef
module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
    es2022: true,
  },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
  plugins: ["@typescript-eslint"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  rules: {
    // Style
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
    "no-console": "off",
    "no-debugger": "warn",
    "prefer-const": "warn",
    "no-var": "error",
    eqeqeq: ["error", "smart"],
    curly: ["warn", "all"],
    "no-throw-literal": "error",

    // TypeScript — relax for pragmatism (no parserOptions.project → no type-aware rules)
    "@typescript-eslint/no-explicit-any": "off",
    "@typescript-eslint/ban-ts-comment": "off",
    "@typescript-eslint/no-require-imports": "off",
    "@typescript-eslint/no-unnecessary-type-assertion": "off",
    "@typescript-eslint/consistent-type-imports": "off",

    // ES modules
    "import/no-unresolved": "off",
  },
  ignorePatterns: [
    "dist/",
    "node_modules/",
    "*.config.*",
    "coverage/",
    "out/",
  ],
  overrides: [
    {
      // Vue SFC files
      files: ["*.vue"],
      parser: "vue-eslint-parser",
      parserOptions: {
        parser: "@typescript-eslint/parser",
        ecmaVersion: 2022,
        sourceType: "module",
        extraFileExtensions: [".vue"],
      },
      extends: [
        "plugin:vue/vue3-recommended",
      ],
      rules: {
        "vue/multi-word-component-names": "off",
        "vue/no-v-html": "off",
        "vue/require-default-prop": "off",
        "vue/max-attributes-per-line": "off",
        "vue/singleline-html-element-content-newline": "off",
      },
    },
    {
      // Test files — relaxed rules
      files: ["tests/**/*.spec.ts", "tests/**/*.ts"],
      rules: {
        "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
        "curly": "off",
      },
    },
    // ── WS-5 followup : garde-fou anti cross-layer imports ──────────────
    // Chaque couche ne peut importer que la couche directement inférieure
    // + packages/shared (le contrat). Les dépendances inverses sont interdites.
    // Cf. ARCHITECTURE.md pour le diagramme complet.
    {
      // RENDERER : ne peut PAS importer du main process (Electron, SQL, IPC handlers).
      // Le renderer traverse l'IPC uniquement via window.novelTradAPI (preload bridge).
      files: ["apps/desktop/src/renderer/**/*.{ts,vue}"],
      rules: {
        "@typescript-eslint/no-restricted-imports": ["error", {
          patterns: [
            {
              group: ["**/apps/desktop/src/main/**", "../../main/**", "../main/**"],
              message: "Renderer ne peut pas importer du main process. Utiliser window.novelTradAPI (preload bridge) pour traverser l'IPC.",
            },
            {
              group: ["electron", "node:*"],
              importNames: ["ipcRenderer", "ipcMain", "BrowserWindow", "app", "dialog", "Menu", "session"],
              message: "Imports Electron interdits dans le renderer. L'IPC passe par window.novelTradAPI.",
            },
          ],
        }],
      },
    },
    {
      // DB : ne peut PAS importer des managers ni services (couche supérieure).
      // La DB est la couche la plus basse (après shared) et ne dépend de rien d'autre.
      files: ["apps/desktop/src/main/db/**/*.ts"],
      rules: {
        "@typescript-eslint/no-restricted-imports": ["error", {
          patterns: [
            {
              group: ["../managers/**", "../services/**", "../ipc/**", "../plugins/**"],
              message: "La couche DB ne peut pas importer des managers/services/ipc (couche supérieure). Architecture en couches — cf. ARCHITECTURE.md.",
            },
          ],
        }],
      },
    },
    {
      // IPC HANDLERS : ne peuvent PAS importer du renderer (vue/pinia/router).
      // Les handlers sont dans le main process et communiquent via IPC uniquement.
      files: ["apps/desktop/src/main/ipc/**/*.ts"],
      rules: {
        "@typescript-eslint/no-restricted-imports": ["error", {
          patterns: [
            {
              group: ["vue", "pinia", "vue-router"],
              message: "Imports renderer interdits dans les IPC handlers (main process).",
            },
            {
              group: ["**/renderer/**"],
              message: "Les IPC handlers ne peuvent pas importer du renderer (main process).",
            },
          ],
        }],
      },
    },
  ],
};
