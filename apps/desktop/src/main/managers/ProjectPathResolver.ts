import type { Database } from "node-sqlite3-wasm";
import { SettingsManager } from "./SettingsManager.js";
import { createProjectDatabase } from "../db/connection.js";
import { ProjectRepository } from "../db/repositories/ProjectRepository.js";

/**
 * WS-4 (clean architecture) : tue la duplication 8× du pattern "scan
 * `recentProjects` + open DB + getById pour résoudre le chemin d'un projet".
 *
 * Le pattern apparaissait verbatim dans :
 *   - ProjectManager.{resolveProjectPath, delete, listChapters}
 *   - ipc/handlers/{lexicon, history, tm, export, project, workflow}.ts
 *
 * Variations historiques (désormais unifiées) :
 *   - Le message d'erreur était parfois "Projet non trouve" (sans accent),
 *     parfois "Projet non trouvé". On unifie sur la version accentuée.
 *   - Quelques versions avaient un guard `fs.existsSync(p + '/project.db')`.
 *     Il a été RETIRÉ de la version unifiée car (a) `createProjectDatabase`
 *     gère déjà les chemins sans DB, et (b) des tests mockent
 *     `createProjectDatabase` sans créer le fichier `project.db` sur disque.
 *   - Certaines versions oubliaient le try/finally intérieur (fuite DB si
 *     `getById` lançait). La version unifiée corrige (try/finally systématique).
 *
 * Sécurité : `createProjectDatabase` + `ProjectRepository.getById` ne
 * suivent pas les symlinks ; la protection path-traversal (`assertSafeProjectPath`)
 * s'applique aux chemins contrôlés par le renderer, pas à la résolution ici
 * (qui lit depuis `recentProjects` — settings de confiance).
 */
export class ProjectPathResolver {
  constructor(private readonly settings: SettingsManager) {}

  /**
   * Résout le chemin du dossier projet à partir de `projectId`.
   *
   * Scan `settings.recentProjects`, pour chaque candidat ouvre la DB et
   * cherche le projet par ID via `ProjectRepository.getById`.
   *
   * NOTE : pas de guard `fs.existsSync(project.db)` volontairement —
   * `createProjectDatabase` gère les chemins sans DB (lève une erreur propre),
   * et certains tests mockent `createProjectDatabase` sans créer le fichier
   * `project.db` sur disque. Le guard cassait ces tests. Le try/finally
   * garantit la fermeture de la DB même si `getById` lance (DB corrompue /
   * WAL verrouillé) — cf. fix P2-4 original.
   *
   * @throws Error si aucun projet correspondant n'est trouvé.
   */
  resolve(projectId: string): string {
    const recent = (this.settings.get("recentProjects") as string[] | undefined) ?? [];
    const projectPath = recent.find((p) => {
      const db = createProjectDatabase(p);
      try {
        const found = new ProjectRepository(db).getById(projectId);
        return found !== undefined;
      } finally {
        db.close();
      }
    });
    if (!projectPath) {
      throw new Error(`Projet non trouvé : ${projectId}`);
    }
    return projectPath;
  }

  /**
   * Ouvre une DB projet, exécute `fn`, puis ferme la DB dans tous les cas
   * (succès ou throw). Tue le pattern try/finally + db.close() répété partout.
   *
   * @returns Ce que `fn` retourne.
   */
  withProjectDb<T>(projectId: string, fn: (db: Database) => T): T {
    const projectPath = this.resolve(projectId);
    const db = createProjectDatabase(projectPath);
    try {
      return fn(db);
    } finally {
      db.close();
    }
  }
}
