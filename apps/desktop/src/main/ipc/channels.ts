// v3 : canaux IPC épurés (79 → ~45).
//
// Supprimés en Phase 3 :
//   - plugin:* (9) — système de plugins supprimé.
//   - history:* + audit:* (7) — historique/snapshots/rollback supprimés.
//   - workflow:pause/resume/retry-step/retry-from/quality-failed/resume-batch/
//     list-active (7) — le SimpleWorkflowRunner est start/cancel only (pas de
//     pause persistante, pas de QA auto-retry branching, pas de jobs table).
//   - ai:stream-* (4) — chat streaming standalone inutilisé en v3
//     (lexicon:suggest construit son propre AiRouter).
//
// Conservés : project CRUD, import/export, workflow start/cancel/progress/
// list, lexicon, ollama, settings, chapter, tm, update, dialog, app, log.
export const IPC_CHANNELS = [
  // project
  "project:create",
  "project:open",
  "project:list-recent",
  "project:path",
  "project:delete",
  "project:stats",
  "project:refresh-source",
  "project:detect-duplicate",
  "project:open-dialog",
  // ollama
  "ollama:list-models",
  "ollama:pull-model",
  "ollama:pull-progress",
  "ollama:is-available",
  "ollama:test-model",
  // settings
  "settings:get",
  "settings:set",
  // workflow (v3 : start/start-batch/cancel/progress/list)
  "workflow:start",
  "workflow:start-batch",
  "workflow:cancel",
  "workflow:progress",
  "workflow:list",
  // lexicon
  "lexicon:list",
  "lexicon:save",
  "lexicon:delete",
  "lexicon:import",
  "lexicon:export",
  "lexicon:extract-candidates",
  "lexicon:find-conflicts",
  "lexicon:suggest",
  // chapter / source / paragraph
  "chapter:list",
  "chapter:import",
  "chapter:get-paragraphs",
  "chapter:save",
  "source:import-files",
  // export
  "export:run",
  "export:batch",
  // dialogs
  "dialog:open-file",
  "dialog:save-file",
  // update (auto-updater)
  "update:check",
  "update:download",
  "update:install",
  "update:set-channel",
  "update:checking",
  "update:available",
  "update:not-available",
  "update:progress",
  "update:downloaded",
  "update:error",
  // translation memory
  "tm:import",
  "tm:export",
  // misc
  "log",
  "app:get-version",
] as const;

export type IpcChannel = (typeof IPC_CHANNELS)[number];
