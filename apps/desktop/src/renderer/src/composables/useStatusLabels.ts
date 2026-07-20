import type { Job, Step, WorkflowStage } from "@shared/types/index.js";

/**
 * WS-6 (clean architecture) : centralise les maps de labels/icônes/classes
 * de statut qui étaient dupliquées à travers 9 endroits du renderer
 * (WorkflowView, PluginsView, HistoryView, ChaptersView, ConsoleView,
 * NtDiffViewer, NtLogViewer, ProjectView).
 *
 * Source unique = ce module. Les variations historiques (certaines views
 * avaient "Annulée" vs "Annulé", ou oubliaient "skipped") sont unifiées sur
 * la version la plus complète (WorkflowView).
 *
 * Exporté sous forme de fonctions pures (pas besoin d'état réactif) — peut
 * s'utiliser dans <script setup> directement via import.
 */

// ── Statuts de workflow (job/step) ──────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  pending: "En attente",
  running: "En cours",
  completed: "Terminé",
  failed: "Échoué",
  skipped: "Ignoré",
  paused: "En pause",
  cancelled: "Annulé",
};

const STATUS_ICONS: Record<string, string> = {
  pending: "\u23F3", // ⏳
  running: "\u{1F504}", // 🔄
  completed: "\u2705", // ✅
  failed: "\u274C", // ❌
  skipped: "\u23ED\uFE0F", // ⏭️
  paused: "\u23F8\uFE0F", // ⏸️
  cancelled: "\u26D4\uFE0F", // ⛔
};

/** Label français d'un statut de job/step. Fallback : le statut brut. */
export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

/** Icône unicode pour un statut. Fallback : sablier. */
export function statusIcon(status: string): string {
  return STATUS_ICONS[status] ?? "\u23F3";
}

// ── Classes CSS de statut ───────────────────────────────────────────────

/** Classe CSS pour le statut d'une étape (step--completed, etc.). */
export function stepStatusClass(status: Step["status"]): string {
  switch (status) {
    case "completed":
      return "step--completed";
    case "running":
      return "step--running";
    case "failed":
      return "step--failed";
    case "skipped":
      return "step--skipped";
    default:
      return "";
  }
}

/** Classe CSS pour le statut d'un job (job--completed, etc.). */
export function jobStatusClass(status: Job["status"]): string {
  switch (status) {
    case "completed":
      return "job--completed";
    case "running":
      return "job--running";
    case "failed":
      return "job--failed";
    case "cancelled":
      return "job--cancelled";
    case "paused":
      return "job--paused";
    default:
      return "";
  }
}

// ── Stages du pipeline ──────────────────────────────────────────────────

const STAGE_LABELS: Record<WorkflowStage, string> = {
  split: "Découpage",
  pre_translate: "Pré-traduction",
  translate: "Traduction IA",
  consistency: "Cohérence",
  lexicon: "Lexique",
  grammar: "Grammaire",
  style: "Style",
  polish: "Polish",
  review: "Réviseur",
  revise: "Correcteur",
  qa: "QA",
  export: "Export",
};

/** Label français d'un stage du pipeline. Fallback : le stage brut. */
export function stageLabel(stage: WorkflowStage): string {
  return STAGE_LABELS[stage] ?? stage;
}

/**
 * Composable wrapper — pour parité d'usage avec le pattern `useXxx()` de Vue.
 * Retourne toutes les fonctions de labels regroupées. Les fonctions peuvent
 * aussi être importées individuellement (elles sont pures).
 */
export function useStatusLabels() {
  return {
    statusLabel,
    statusIcon,
    stepStatusClass,
    jobStatusClass,
    stageLabel,
  };
}
