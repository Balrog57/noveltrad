/**
 * WS-6 (clean architecture) : helper de téléchargement Blob partagé.
 *
 * Avant, le pattern "créer un Blob + URL.createObjectURL + <a> cliquable +
 * revokeObjectURL" était inline dans LexiconView.doExport et ExportDialog.
 * Centralisation = source unique + libération mémoire garantie.
 */

/**
 * Déclenche le téléchargement d'un Blob côté navigateur.
 *
 * @param blob  Le contenu à télécharger.
 * @param filename Nom du fichier proposé à l'utilisateur.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Libérer l'URL après le click. Le timeout laisse au navigateur le temps
  // d'initier le téléchargement avant que l'URL ne soit invalidée.
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
