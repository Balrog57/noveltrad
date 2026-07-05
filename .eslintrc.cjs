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
  ],
};
