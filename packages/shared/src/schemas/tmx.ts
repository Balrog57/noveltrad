import { z } from "zod";

export const tmxImportSchema = z.object({
  projectId: z.string().uuid(),
  filePath: z.string().min(1),
});

export const tmxExportSchema = z.object({
  projectId: z.string().uuid(),
  filePath: z.string().min(1),
});
