/**
 * Plugin d'exemple : Export PDF pour NovelTrad
 *
 * Ce plugin ajoute un format d'export "pdf" à l'ExportEngine.
 * Il est pré-compilé en ESM (.mjs) conformément au SDD Volume 15.
 *
 * API NovelTrad utilisée :
 * - context.registerExport(format, renderer) — enregistre un renderer d'export
 * - context.logger — journalisation prefixée par le plugin
 */

export default {
  manifest: {
    id: "com.noveltrad.example-export",
    name: "Export PDF Example",
    version: "1.0.0",
    type: "export",
  },
  apiVersion: "1.0",

  /**
   * Activé par PluginHost. Reçoit un PluginContext.
   */
  activate(context) {
    context.logger.info("Plugin Export PDF activé");

    context.registerExport("pdf", (input) => {
      // Generate a minimal PDF-like buffer
      // In a real plugin, this would use a PDF library
      const lines = [];
      if (input.title) {
        lines.push(`%PDF-1.4`);
        lines.push(`1 0 obj`);
        lines.push(`<< /Type /Catalog /Pages 2 0 R >>`);
        lines.push(`endobj`);
        lines.push(`2 0 obj`);
        lines.push(`<< /Type /Pages /Kids [3 0 R] /Count 1 >>`);
        lines.push(`endobj`);
        lines.push(`3 0 obj`);
        lines.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]`);
        lines.push(`   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>`);
        lines.push(`endobj`);
        lines.push(`4 0 obj`);
        lines.push(`<< /Length 44 >>`);
        lines.push(`stream`);
        lines.push(`BT /F1 12 Tf 72 720 Td (${input.title}) Tj ET`);
        lines.push(`endstream`);
        lines.push(`endobj`);
        lines.push(`5 0 obj`);
        lines.push(`<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`);
        lines.push(`endobj`);
        lines.push(`xref`);
        lines.push(`0 6`);
        lines.push(`0000000000 65535 f `);
        lines.push(`0000000009 00000 n `);
        lines.push(`0000000058 00000 n `);
        lines.push(`0000000115 00000 n `);
        lines.push(`0000000266 00000 n `);
        lines.push(`0000000363 00000 n `);
        lines.push(`trailer << /Size 6 /Root 1 0 R >>`);
        lines.push(`startxref`);
        lines.push(`435`);
        lines.push(`%%EOF`);
      }
      return Buffer.from(lines.join("\n"), "utf-8");
    });
  },

  /**
   * Désactivé par PluginHost. Nettoyage si nécessaire.
   */
  deactivate() {
    // cleanup
  },
};
