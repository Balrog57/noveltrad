import { z } from "zod";

/**
 * Schéma Zod de validation du manifest.json d'un plugin NovelTrad.
 * SDD Volume 15 §15.3, §15.7.
 *
 * Règles :
 * - id : chaîne en kebab-case pointé (ex: com.noveltrad.example)
 * - name : 1-100 caractères
 * - version : semver strict (x.y.z)
 * - type : un des 8 types de plugin définis dans le SDD
 * - entry : chemin vers le point d'entrée (doit être .mjs ou .js, PAS .ts)
 * - permissions : tableau de permissions reconnues
 * - contributions : bloc optionnel
 * - configSchema : schéma JSON optionnel (non validé en profondeur)
 */

const pluginTypeSchema = z.enum([
  "provider",
  "agent",
  "export",
  "prompt-pack",
  "workflow",
  "ui-theme",
  "parser",
  "tool",
]);

const pluginPermissionSchema = z.enum([
  "ai",
  "lexicon",
  "project-read",
  "project-write",
  "fs-read",
  "fs-write",
  "network",
  "ui",
]);

/**
 * Valide que l'entrée ne se termine PAS par .ts.
 * Accepte .mjs, .js, .cjs.
 */
const entrySchema = z
  .string()
  .min(1)
  .refine(
    (val) => {
      const lower = val.toLowerCase();
      return !lower.endsWith(".ts");
    },
    {
      message: "Le point d'entrée doit être un fichier .mjs ou .js compilé, pas .ts",
    },
  )
  .refine(
    (val) => {
      const lower = val.toLowerCase();
      return lower.endsWith(".mjs") || lower.endsWith(".js") || lower.endsWith(".cjs");
    },
    {
      message: "Le point d'entrée doit avoir une extension .mjs, .js ou .cjs",
    },
  );

const agentContributionSchema = z.object({
  stage: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
});

const exportContributionSchema = z.object({
  format: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
});

const providerContributionSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
});

const parserContributionSchema = z.object({
  extension: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
});

const promptContributionSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  description: z.string().optional(),
});

const commandContributionSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  handler: z.string().optional(),
});

const contributionsSchema = z
  .object({
    agents: z.array(agentContributionSchema).optional(),
    exports: z.array(exportContributionSchema).optional(),
    providers: z.array(providerContributionSchema).optional(),
    parsers: z.array(parserContributionSchema).optional(),
    prompts: z.array(promptContributionSchema).optional(),
    commands: z.array(commandContributionSchema).optional(),
  })
  .optional();

export const pluginManifestSchema = z.object({
  id: z
    .string()
    .min(1)
    .regex(/^[a-z0-9.-]+$/, {
      message: "L'id du plugin doit être en minuscules, chiffres, points et tirets uniquement",
    }),
  name: z.string().min(1).max(100),
  version: z.string().regex(/^\d+\.\d+\.\d+$/, {
    message: "La version doit être au format semver (x.y.z)",
  }),
  author: z.string().optional(),
  description: z.string().optional(),
  type: pluginTypeSchema,
  entry: entrySchema,
  permissions: z.array(pluginPermissionSchema).default([]),
  contributions: contributionsSchema,
  configSchema: z
    .record(z.unknown())
    .optional()
    .refine(
      (val) => {
        if (!val) return true;
        return JSON.stringify(val).length < 10000;
      },
      { message: "configSchema trop volumineux (max 10 Ko)" },
    ),
});

export type PluginManifestInput = z.input<typeof pluginManifestSchema>;
export type PluginManifestOutput = z.output<typeof pluginManifestSchema>;
