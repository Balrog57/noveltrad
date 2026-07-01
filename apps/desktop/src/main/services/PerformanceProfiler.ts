/**
 * PerformanceProfiler — SDD §22.6
 *
 * Collecte les métriques de performance par étape de workflow :
 * - durationMs : temps d'exécution de l'étape
 * - tokensIn / tokensOut : tokens consommés par l'étape (si fournis par le LLM)
 * - memoryPeakMB : pic de mémoire du processus lors de l'étape
 *
 * Les données sont stockées en mémoire (Map) et peuvent être exportées en CSV.
 */

export interface PerformanceMetrics {
  /** Identifiant du job */
  jobId: string;
  /** Nom de l'étape (stage) */
  stage: string;
  /** Durée en millisecondes */
  durationMs: number;
  /** Tokens en entrée (fournis par le LLM, optionnel) */
  tokensIn?: number;
  /** Tokens en sortie (fournis par le LLM, optionnel) */
  tokensOut?: number;
  /** Pic mémoire en Mo, mesuré par `process.memoryUsage()` */
  memoryPeakMB: number;
  /** Horodatage de la collecte */
  collectedAt: string;
}

/** Métriques partielles collectées avant enrichissement */
export interface PartialMetrics {
  durationMs: number;
  tokensIn?: number;
  tokensOut?: number;
}

type MetricsStore = Map<string, PerformanceMetrics[]>;

export class PerformanceProfiler {
  private store: MetricsStore = new Map();

  /**
   * Collecte les métriques pour une étape d'un job.
   * Mesure automatiquement le pic mémoire via `process.memoryUsage()`.
   *
   * @param jobId  Identifiant du job
   * @param stage  Nom de l'étape
   * @param metrics  Métriques partielles (durationMs, tokensIn/out optionnels)
   */
  collect(
    jobId: string,
    stage: string,
    metrics: PartialMetrics,
  ): PerformanceMetrics {
    const memUsage = this.getMemoryPeakMB();
    const entry: PerformanceMetrics = {
      jobId,
      stage,
      durationMs: metrics.durationMs,
      tokensIn: metrics.tokensIn,
      tokensOut: metrics.tokensOut,
      memoryPeakMB: memUsage,
      collectedAt: new Date().toISOString(),
    };

    const existing = this.store.get(jobId) ?? [];
    existing.push(entry);
    this.store.set(jobId, existing);

    return entry;
  }

  /**
   * Retourne toutes les métriques collectées pour un job donné.
   * @param jobId  Identifiant du job
   * @returns Tableau des métriques (vide si job inconnu)
   */
  getReport(jobId: string): PerformanceMetrics[] {
    return this.store.get(jobId) ?? [];
  }

  /**
   * Retourne la liste de tous les jobIds ayant des métriques collectées.
   */
  getJobIds(): string[] {
    return Array.from(this.store.keys());
  }

  /**
   * Retourne toutes les métriques de tous les jobs.
   */
  getAllMetrics(): PerformanceMetrics[] {
    const all: PerformanceMetrics[] = [];
    for (const metrics of this.store.values()) {
      all.push(...metrics);
    }
    return all;
  }

  /**
   * Exporte toutes les métriques collectées au format CSV.
   *
   * @returns Chaîne CSV avec en-têtes
   */
  exportCsv(): string {
    const headers = [
      "jobId",
      "stage",
      "durationMs",
      "tokensIn",
      "tokensOut",
      "memoryPeakMB",
      "collectedAt",
    ];
    const rows: string[] = [];

    for (const metrics of this.store.values()) {
      for (const entry of metrics) {
        rows.push(
          [
            this.escapeCsv(entry.jobId),
            this.escapeCsv(entry.stage),
            String(entry.durationMs),
            entry.tokensIn != null ? String(entry.tokensIn) : "",
            entry.tokensOut != null ? String(entry.tokensOut) : "",
            String(entry.memoryPeakMB),
            this.escapeCsv(entry.collectedAt),
          ].join(","),
        );
      }
    }

    return headers.join(",") + "\n" + rows.join("\n") + "\n";
  }

  /**
   * Vide toutes les métriques collectées (utile pour les tests).
   */
  clear(): void {
    this.store.clear();
  }

  /**
   * Mesure le pic mémoire du processus en Mo.
   * Utilise `process.memoryUsage().heapUsed` disponible dans Node.js.
   */
  private getMemoryPeakMB(): number {
    try {
      const usage = process.memoryUsage();
      return Math.round((usage.heapUsed / 1024 / 1024) * 100) / 100;
    } catch {
      return 0;
    }
  }

  /**
   * Échappe les guillemets et entoure de guillemets si nécessaire pour le CSV.
   */
  private escapeCsv(value: string): string {
    if (value.includes('"') || value.includes(",") || value.includes("\n")) {
      return `"${value.replace(/"/g, '""')}"`;
    }
    return value;
  }
}
