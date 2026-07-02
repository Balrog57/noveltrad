import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@shared": path.resolve(__dirname, "../../packages/shared/src"),
      "@scripts": path.resolve(__dirname, "../../scripts"),
    },
  },
  test: {
    globals: true,
    environment: "node",

    include: ["tests/unit/**/*.spec.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: [
        "src/main/services/**/*.ts",
        "src/main/managers/**/*.ts",
        "src/main/db/repositories/**/*.ts",
        "src/main/ipc/handlers/**/*.ts",
      ],
      thresholds: {
        statements: 40,
        branches: 50,
        functions: 75,
        lines: 40,
      },
    },
  },
});
