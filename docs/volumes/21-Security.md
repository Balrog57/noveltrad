# Volume 21 — Sécurité

## 21.1 Modèle de menaces

### Acteurs

| Acteur | Capacité |
|--------|----------|
| Utilisateur légitime | Utilise l’application normalement. |
| Attaquant avec accès fichier | Peut lire/modifier les fichiers projet. |
| Attaquant réseau | Peut intercepter ou altérer les communications. |
| Plugin malveillant | Exécute du code dans le main process. |
| Fournisseur IA compromis | Retourne des réponses malveillantes. |

### Actifs

- Clés API des providers IA.
- Bases SQLite des projets.
- Fichiers source et traductions.
- Logs potentiellement sensibles.

---

## 21.2 Sandbox Electron

Depuis Electron 12, le **sandbox** est activé par défaut pour les `BrowserWindow`. NovelTrad n'utilise pas `app.enableSandbox()` (API non standard) et s'appuie sur les `webPreferences` explicites suivantes :

```typescript
const mainWindow = new BrowserWindow({
  webPreferences: {
    sandbox: true,
    contextIsolation: true,
    nodeIntegration: false,
    allowRunningInsecureContent: false,
    webSecurity: true,
    preload: path.join(__dirname, 'preload.js')
  }
})
```

### Points clés

- `sandbox: true` : le renderer n'a pas d'accès Node.js natif.
- `contextIsolation: true` : le contexte preload est isolé du contexte page (obligatoire depuis Electron 12).
- `nodeIntegration: false` : interdit l'usage de `require` côté renderer.
- `allowRunningInsecureContent: false` : bloque le contenu mixte HTTP/HTTPS.
- `webSecurity: true` : active la politique de même origine.

**Référence** (Context7: `/electron/electron`) : sandboxing and context isolation are the current security baseline.

---

## 21.3 Validation IPC

### Liste blanche de canaux

Seuls les canaux déclarés dans `src/main/ipc/channels.ts` sont acceptés. Les canaux inconnus sont rejetés.

### Validation Zod

Tous les payloads sont validés avec Zod avant traitement. Voir Volume 16.

### Prévention des injections

- Aucun chemin fichier n’est passé directement à `fs` sans validation.
- Les chemins sont résolus avec `path.resolve` et vérifiés contre le dossier projet autorisé.

```typescript
function assertWithinProject(basePath: string, targetPath: string): void {
  const resolved = path.resolve(targetPath)
  if (!resolved.startsWith(path.resolve(basePath))) {
    throw new Error('Path traversal detected')
  }
}
```

---

### Tests de path traversal

La fonction `assertWithinProject` doit être couverte par des tests unitaires au moins sur les cas suivants :

| Cas | Chemin cible | Résultat attendu |
|---|---|---|
| Chemin normal dans le projet | `MonProjet/source/ch001.md` | ✅ accepté |
| Remontée directe | `MonProjet/../secret.txt` | ❌ rejeté |
| Remontée encodée | `MonProjet/%2e%2e%2fsecret.txt` | ❌ rejeté (décodé avant validation) |
| Lien symbolique hors projet | `MonProjet/link-to-etc` pointant vers `/etc` | ❌ rejeté (résolution réelle du symlink) |
| Chemin absolu hors projet | `/etc/passwd` | ❌ rejeté |
| Séparateurs mélangés (Windows) | `MonProjet\\..\\secret.txt` | ❌ rejeté |

```typescript
it('rejects path traversal outside project', () => {
  expect(() => assertWithinProject('/projects/MonProjet', '/projects/MonProjet/../secret.txt'))
    .toThrow('Path traversal detected')
})

it('resolves symlinks before validation', () => {
  // symlink /projects/MonProjet/link -> /etc
  expect(() => assertWithinProject('/projects/MonProjet', '/projects/MonProjet/link/passwd'))
    .toThrow('Path traversal detected')
})
```
## 21.4 Permissions

### Accès fichier

- Le main process n’accède qu’aux dossiers explicitement autorisés :
  - Dossier projet courant.
  - Dossier de configuration utilisateur.
  - Dossier de téléchargements temporaires.

### Pas d’exécution arbitraire

- `eval`, `new Function`, `child_process.exec` interdits sauf dans des cas contrôlés.
- Les plugins ne peuvent pas exécuter de commandes shell.

### Plugins

- Chaque plugin déclare ses permissions.
- L’utilisateur confirme l’installation.
- Voir Volume 15 pour le modèle de permissions.

---

### Plugins (v1.0 sans sandbox isolé)

En v1.0, les plugins s'exécutent dans le **main process** avec les mêmes privilèges que NovelTrad. Il n'existe pas de sandbox V8 isolé pour les plugins (complexité élevée, reporté en v2.0). Le modèle de confiance repose donc sur les barrières suivantes :

- **Manifest validé** : `manifest.json` est parsé et validé avec Zod avant chargement.
- **Permissions explicites** : chaque plugin déclare les permissions requises (`ai`, `lexicon`, `project-read`, `project-write`, `fs-read`, `fs-write`, `network`, `ui`).
- **Confirmation utilisateur** : l'installation ou l'activation d'un plugin demandant `project-write`, `fs-write`, `network` ou `ui` requiert une confirmation explicite.
- **Pas d'accès IPC direct** : un plugin ne peut pas appeler `ipcMain` ou accéder aux canaux non exposés par `PluginContext`.
- **Pas d'exécution arbitraire** : `eval`, `new Function` et `child_process.exec` sont interdits ; le plugin doit passer par les API déclarées.
- **Clés API non transmises** : les clés ne sont jamais passées au plugin ; les appels IA transitent obligatoirement par `AiRouter`.
- **Scope fichier limité** : les écritures via `fs-write` sont restreintes au dossier projet, sauf permission explicite justifiée et confirmée.
- **Signature (v2.0)** : le marketplace v2.0 exigera une signature vérifiée avant l'installation automatique.

**Recommandation v1.0.** Ne charger que des plugins provenant de sources connues ou audités, et désactiver le hot-reload en production.
## 21.5 Protection des fichiers

### Base SQLite

- Chiffrement optionnel avec SQLCipher.
- Clé dérivée du mot de passe utilisateur ou du keyring OS.
- En v1.0, le chiffrement est optionnel.

### Clés API

NovelTrad stocke les clés API des providers cloud selon la hiérarchie suivante :

1. **Keyring OS via `keytar`** (option privilégiée) : les clés sont déposées dans le trousseau sécurisé du système (Windows Credential Locker, macOS Keychain, Linux libsecret). C'est la méthode recommandée en production.
2. **Fichier chiffré local** (fallback) : si `keytar` n'est pas disponible, les clés sont chiffrées avec **AES-256-GCM** dans un fichier utilisateur (`~/.noveltrad/secrets.json` ou `%APPDATA%/NovelTrad/secrets.json`). La clé de chiffrement est dérivée d'un identifiant machine stable + d'un mot de passe utilisateur si l'authentification est activée.

**Règles communes.**
- Les clés ne sont **jamais** loguées (même partiellement).
- Les clés ne sont **jamais** transmises au renderer ; seul le main process les utilise via `AiRouter`.
- Les clés ne sont **jamais** exposées aux plugins ; les plugins passent par `AiRouter`.
- L'UI affiche uniquement un masque (`sk-...XXXX`) lors de la configuration.

---

## 21.6 Content Security Policy

```typescript
session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
  callback({
    responseHeaders: {
      ...details.responseHeaders,
      'Content-Security-Policy': ["default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"]
    }
  })
})
```

---

## 21.7 Audit IPC

### Canaux sensibles

| Canal | Risque | Mitigation |
|-------|--------|------------|
| `project:open` | Path traversal | Vérifier `project.db` existe. |
| `chapter:import` | Écriture hors projet | Valider le dossier cible. |
| `model:test` | Fuite de clé API | Ne pas loguer la clé. |
| `settings:set` | Modification non autorisée | Valider la clé et la valeur. |

### Revue périodique

- Liste des canaux IPC auditée à chaque release.
- Tests de sécurité automatisés (path traversal, validation Zod).

---

## 21.8 Communications réseau

### HTTPS obligatoire

- Tous les appels cloud (OpenAI, Anthropic, etc.) passent par HTTPS.
- `electron-updater` vérifie les signatures et hashes.

### Certificats

- Refuser les certificats auto-signés sauf option de debug activée.

---

## 21.9 Mise à jour sécurisée

- Vérification SHA256/SHA512 via `electron-updater`.
- Signature Authenticode Windows / Apple macOS.
- Rollback en cas d’échec. Voir Volume 17.

---

## ✅ Critères d’acceptation sécurité

- [ ] Le preload script n’expose pas `ipcRenderer` directement.
- [ ] Les canaux IPC sont validés et inconnus rejetés.
- - [ ] Les clés API ne sont pas en clair dans les logs.
- [ ] Les clés API sont stockées dans le keyring OS (keytar) ou dans un fichier chiffré AES-256-GCM, jamais dans le renderer.
- - [ ] Le sandbox est activé par défaut (Electron 12+) et renforcé via webPreferences.
- [ ] Le sandbox est activé.
- [ ] Les plugins demandent une confirmation d’installation.
- [ ] Les chemins fichiers sont validés contre le projet autorisé.
- [ ] Une CSP stricte est appliquée.
- [ ] Les communications réseau passent par HTTPS.

---

## 📚 Références Context7

- `/electron/electron` — Sécurité Electron, sandbox, contextBridge, CSP.
