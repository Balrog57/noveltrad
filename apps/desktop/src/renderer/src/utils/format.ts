/**
 * WS-6 (clean architecture) : helpers de formatage partagés.
 *
 * Avant, chaque vue (Console, Project, Workflow, History, Lexicon) inlineait
 * ses propres formatDate/formatDuration/formatSize avec des variations
 * subtiles. Centralisation = source unique + cohérence UI.
 */

/**
 * Formate une date ISO/epoch en chaîne lisible (format local court).
 * @param value ISO string, epoch ms, ou Date.
 */
export function formatDate(value: string | number | Date | null | undefined): string {
  if (value === null || value === undefined || value === "") {return "—";}
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {return "—";}
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Formate une durée en ms vers "Xs", "Xm Ys", "Xh Ym".
 * @param ms Durue en millisecondes (0 ou négatif → "—").
 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms <= 0) {return "—";}
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) {return `${h}h ${m}m`;}
  if (m > 0) {return `${m}m ${s}s`;}
  return `${s}s`;
}

/**
 * Formate un timestamp (epoch ms ou Date) en "HH:MM:SS".
 * Utilisé par les viewers de logs (ConsoleView, NtLogViewer).
 */
export function formatTime(value: number | string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {return "??:??:??";}
  return date.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

/**
 * Formate un nombre d'octets vers "1.2 Ko", "3.4 Mo", etc.
 */
export function formatSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || bytes <= 0) {return "0 o";}
  const units = ["o", "Ko", "Mo", "Go", "To"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}
