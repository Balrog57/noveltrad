/**
 * WS-5 (clean architecture) : extrait la responsabilité pause/resume/cancel
 * du WorkflowRunner.
 *
 * État isolé :
 *   - `paused` / `cancelled` : flags booléens lus par les boucles de run
 *   - `resumeFn` : gate Promise (remplace l'ancien EventEmitter qui ne servait
 *     qu'à émettre un unique événement "resume")
 *
 * Le WorkflowRunner délègue à ce contrôleur via `this.pauseCtl`. Toute la
 * logique de coordination pause/resume/cancel est ici, testable isolément.
 *
 * Sémantique préservée à l'identique (cf. P0-1/P0-2 fixes du WorkflowRunner
 * original — les race start/startBatch et la double fermeture DB restent du
 * ressort du runner ; le PauseController ne fait que l'état pause/cancel).
 */
export class PauseController {
  private paused = false;
  private cancelled = false;
  /**
   * Gate de pause/resume basée sur une Promise. `resumeFn` est la fonction
   * de résolution capturée à la création de la Promise d'attente ; l'appeler
   * débloque `waitForResume()`. Une seule pause peut être en attente à la fois.
   */
  private resumeFn: (() => void) | null = null;

  get isPaused(): boolean {
    return this.paused;
  }

  get isCancelled(): boolean {
    return this.cancelled;
  }

  pause(): void {
    this.paused = true;
  }

  /**
   * Reprend le workflow. Résout la Promise d'attente de `waitForResume()` si
   * une pause est en cours. Remplace l'ancien `EventEmitter.emit("resume")`.
   */
  resume(): void {
    this.paused = false;
    if (this.resumeFn) {
      const fn = this.resumeFn;
      this.resumeFn = null;
      fn();
    }
  }

  cancel(): void {
    this.cancelled = true;
    // Si une pause est en cours, la débloquer pour que les boucles de run
    // puissent atteindre le check `cancelled` et sortir.
    this.resume();
  }

  /**
   * Retourne une Promise qui se résout quand `resume()` est appelé.
   * Remplace l'ancien pattern `EventEmitter.once("resume", ...)`.
   *
   * Une seule pause peut être en attente à la fois (les boucles while/paused
   * sont séquentielles) ; on stocke donc un unique `resumeFn`.
   */
  waitForResume(): Promise<void> {
    return new Promise<void>((resolve) => {
      this.resumeFn = resolve;
    });
  }
}
