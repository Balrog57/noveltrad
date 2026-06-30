import { ipcMain } from "electron";
import { z } from "zod";
import { ExportEngine } from "../../services/ExportEngine.js";
import { exportRunSchema } from "@shared/schemas/export.js";
import type { ExportRunResult } from "@shared/schemas/export.js";

const exportEngine = new ExportEngine();

export function registerExportHandlers(): void {
  ipcMain.handle(
    "export:run",
    async (_event, payload): Promise<ExportRunResult> => {
      try {
        const input = exportRunSchema.parse(payload);
        const outputPath = await exportEngine.export(input);

        // Validation post-export : le fichier doit exister, ne pas être vide, taille > 0
        const fs = await import("node:fs");
        if (!fs.existsSync(outputPath)) {
          return {
            success: false,
            error: {
              code: "EXPORT_FAILED",
              message: "Le fichier exporté est introuvable après l'écriture.",
            },
          };
        }
        const stat = fs.statSync(outputPath);
        if (stat.size === 0) {
          return {
            success: false,
            error: {
              code: "EXPORT_FAILED",
              message: "Le fichier exporté est vide.",
            },
          };
        }

        return {
          success: true,
          path: outputPath,
          size: stat.size,
          format: input.format,
        };
      } catch (err) {
        if (err instanceof z.ZodError) {
          return {
            success: false,
            error: {
              code: "VALIDATION_ERROR",
              message: "Données d'export invalides.",
              details: JSON.stringify(err.errors),
            },
          };
        }
        const message =
          err instanceof Error
            ? err.message
            : "Erreur inconnue lors de l'export.";
        return {
          success: false,
          error: { code: "EXPORT_FAILED", message },
        };
      }
    },
  );
}
