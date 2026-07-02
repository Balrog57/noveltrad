/**
 * ESLint configuration for NovelTrad.
 *
 * NOTE: This project uses TypeScript and Vue, but the following peer
 * dependencies are NOT installed in devDependencies and should be added
 * for full type-aware linting:
 *   - @typescript-eslint/parser
 *   - @typescript-eslint/eslint-plugin
 *   - eslint-plugin-vue
 *
 * The current config provides basic JS/Vue linting. Once the plugins
 * above are installed, update parser to @typescript-eslint/parser and
 * enable the recommended TS & Vue rulesets.
 */

// eslint-disable-next-line no-undef
module.exports = {
  root: true,
  env: {
    browser: true,
    node: true,
    es2022: true,
  },
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
  extends: [
    "eslint:recommended",
  ],
  rules: {
    // Style
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "no-console": "off",
    "no-debugger": "warn",
    "prefer-const": "warn",
    "no-var": "error",
    eqeqeq: ["error", "always"],
    curly: ["warn", "all"],
    "no-throw-literal": "error",

    // ES modules
    "import/no-unresolved": "off",
  },
  overrides: [
    {
      // Vue SFC files: use basic parser
      files: ["*.vue"],
      parser: "espree",
      rules: {
        "no-unused-vars": "off", // Vue templates use vars differently
      },
    },
  ],
  ignorePatterns: [
    "dist/",
    "node_modules/",
    "*.config.*",
    "coverage/",
  ],
};
