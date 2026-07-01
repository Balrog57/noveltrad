# Volume 17 — Auto Update

## 17.1 Objectif

NovelTrad 2.0 vérifie automatiquement les nouvelles versions sur GitHub Releases, télécharge l’installeur, le vérifie, puis le lance et redémarre l’application — le tout de manière transparente pour l’utilisateur, comme VS Code.

---

## 17.2 Flux général

```text
Démarrage de l’application
    ↓
Vérification d’une nouvelle release (après 30 s)
    ↓
Nouvelle version disponible ?
    ↓
Notification à l’utilisateur
    ↓
Téléchargement silencieux en arrière-plan
    ↓
Vérification SHA256 / signature
    ↓
Proposition d’installation
    ↓
Installation silencieuse
    ↓
Redémarrage
```

---

## 17.3 Canaux de mise à jour

| Canal | Tag Git | Usage |
|-------|---------|-------|
| `stable` | `v1.2.3` | Tous les utilisateurs. |
| `beta` | `v1.3.0-beta.1` | Testeurs volontaires. |
| `alpha` | `v1.3.0-alpha.1` | Développement interne. |

### Sélection du canal

- Par défaut : `stable`.
- L’utilisateur peut choisir `beta` dans Paramètres → Avancé.
- `electron-updater` filtre automatiquement les releases par version semver incluant le pré-release tag.

### Configuration `electron-builder.yml`

```yaml
publish:
  provider: github
  owner: Balrog57
  repo: noveltrad
  releaseType: release          # publier en release (pas draft)
  channel: latest               # canal par défaut
  generateUpdatesFilesForAllChannels: true

win:
  target:
    - nsis

mac:
  target:
    - dmg

linux:
  target:
    - AppImage
```

**Note.** `releaseType: draft` empêche `electron-updater` de trouver la release car les drafts ne sont pas listés publiquement. En v1.0 on publie en release (pas draft), éventuellement en pré-release GitHub pour beta.

**Référence** (Context7: `/electron-userland/electron-builder`) : `generateUpdatesFilesForAllChannels: true` génère `latest.yml`, `beta.yml`, `alpha.yml` selon le tag semver.

---

## 17.4 Implémentation main process

```typescript
import { autoUpdater } from 'electron-updater'
import { dialog, BrowserWindow } from 'electron'
import { logger } from './logger'

export class UpdateManager extends EventEmitter {
  private checking = false

  constructor(private channel: string = 'latest') {
    super()
    autoUpdater.channel = channel
    autoUpdater.allowDowngrade = false
    autoUpdater.autoDownload = false
    autoUpdater.autoInstallOnAppQuit = false

    autoUpdater.on('checking-for-update', () => {
      logger.info('Checking for updates...')
      this.emit('checking')
    })

    autoUpdater.on('update-available', (info) => {
      logger.info('Update available', info)
      this.emit('available', info)
      this.promptAndDownload()
    })

    autoUpdater.on('update-not-available', () => {
      logger.info('No update available')
      this.emit('not-available')
    })

    autoUpdater.on('download-progress', (progress) => {
      this.emit('progress', progress)
    })

    autoUpdater.on('update-downloaded', (info) => {
      logger.info('Update downloaded', info)
      this.emit('downloaded', info)
      this.promptInstall()
    })

    autoUpdater.on('error', (err) => {
      logger.error('Auto-update error', err)
      this.emit('error', err)
    })
  }

  async check(): Promise<void> {
    if (this.checking) return
    this.checking = true
    try {
      await autoUpdater.checkForUpdates()
    } finally {
      this.checking = false
    }
  }

  private async promptAndDownload(): Promise<void> {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Mise à jour disponible',
      message: 'Une nouvelle version de NovelTrad est disponible.',
      detail: 'Télécharger maintenant et installer au prochain redémarrage ?',
      buttons: ['Télécharger', 'Plus tard'],
      defaultId: 0
    })

    if (response === 0) {
      await autoUpdater.downloadUpdate()
    }
  }

  private async promptInstall(): Promise<void> {
    const { response } = await dialog.showMessageBox({
      type: 'info',
      title: 'Mise à jour prête',
      message: 'La mise à jour a été téléchargée.',
      buttons: ['Installer et redémarrer', 'Plus tard'],
      defaultId: 0
    })

    if (response === 0) {
      autoUpdater.quitAndInstall()
    }
  }
}
```

---

## 17.5 latest.json enrichi

Un manifeste `latest.json` est publié en complément des fichiers `latest.yml`/`latest-mac.yml`/`latest-linux.yml` générés par `electron-builder`.

```json
{
  "version": "1.1.0",
  "channel": "stable",
  "release_date": "2026-07-15T10:00:00Z",
  "download_url": "https://github.com/Balrog57/noveltrad/releases/download/v1.1.0/Setup_NovelTrad-1.1.0.exe",
  "sha256": "a1b2c3...",
  "release_notes_url": "https://github.com/Balrog57/noveltrad/releases/tag/v1.1.0",
  "mandatory": false,
  "min_app_version": "1.0.0"
}
```

### Rôle

- `electron-updater` utilise `latest.yml` pour Windows, `latest-mac.yml` pour macOS.
- `latest.json` sert à :
  - Afficher les notes de version.
  - Forcer une mise à jour obligatoire (`mandatory`).
  - Bloquer les anciennes versions (`min_app_version`).
  - Permettre un fallback si `electron-updater` échoue.

---

## 17.5b Génération et mise à jour de `latest.json`

`latest.json` n’est pas généré automatiquement par `electron-builder`. Il est produit par la CI à partir des métadonnées de la release.

### Script de génération (CI)

```typescript
// scripts/generate-latest-json.ts
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'

interface LatestManifest {
  version: string
  channel: 'stable' | 'beta' | 'alpha'
  release_date: string
  download_url: string
  sha256: string
  release_notes_url: string
  mandatory: boolean
  min_app_version: string
}

function generateLatestJson(
  version: string,
  channel: string,
  installerPath: string,
  owner: string,
  repo: string
): LatestManifest {
  const sha256 = createHash('sha256').update(readFileSync(installerPath)).digest('hex')
  return {
    version,
    channel: channel as 'stable' | 'beta' | 'alpha',
    release_date: new Date().toISOString(),
    download_url: `https://github.com/${owner}/${repo}/releases/download/v${version}/Setup_NovelTrad-${version}.exe`,
    sha256,
    release_notes_url: `https://github.com/${owner}/${repo}/releases/tag/v${version}`,
    mandatory: false,
    min_app_version: '1.0.0'
  }
}
```

### Processus dans la CI

1. Build + packaging par `electron-builder`.
2. Calcul du SHA256 de l’installeur Windows.
3. Écriture de `latest.json` avec le script ci-dessus.
4. Upload de `latest.json` comme asset de la release GitHub.
5. Upload des `latest*.yml` générés par `electron-builder`.

### Mise à jour manuelle

- Modifier `mandatory` ou `min_app_version` dans `latest.json` uniquement pour forcer une mise à jour critique.
- Toujours versionner le fichier source dans le repo (`assets/latest.json.template`) pour tracer les changements.

---

## 17.6 Vérification de l’intégrité

### SHA256

- `latest.yml` contient déjà un hash SHA512.
- `electron-updater` vérifie automatiquement le hash après téléchargement.
- `latest.json` fournit un SHA256 redondant pour vérification manuelle/fallback.

### Signature Windows

- Si un certificat Authenticode est configuré (`CSC_LINK`, `CSC_KEY_PASSWORD`), `electron-builder` signe l’installeur.
- Windows vérifie la signature au lancement.

### Signature macOS

- `hardenedRuntime: true`
- `gatekeeperAssess: false`
- `entitlements` configurées.

---

## 17.7 Stratégies de rollback

### Rollback automatique

- Si l’installation échoue (signature invalide, fichier corrompu), l’application conserve la version précédente.
- `electron-updater` ne remplace l’exécutable que si la vérification réussit.

### Rollback manuel

- L’utilisateur peut télécharger une ancienne version depuis GitHub Releases.
- L’application maintient une page “Versions précédentes” dans Paramètres.

### Downgrade

- `autoUpdater.allowDowngrade = false` par défaut.
- Possible sur les canaux beta/alpha si nécessaire.

---

## 17.8 Gestion des erreurs

| Scénario | Comportement |
|----------|--------------|
| GitHub indisponible | Retry silencieux ×3, puis notification discrète. |
| Pas de connexion internet | Vérification reportée au prochain démarrage. |
| Téléchargement interrompu | Reprise depuis le début (pas de delta en v1.0). |
| Vérification SHA échoue | Suppression du fichier, alerte utilisateur. |
| Signature invalide | Blocage, proposition de téléchargement manuel. |
| Utilisateur refuse l’update | Mémoriser le choix, ne pas re-demander avant 24 h. |

---

## 17.9 UI de mise à jour

### Toast / Modal

- Notification non intrusive : “Une mise à jour est disponible”.
- Modal complet si la mise à jour est obligatoire.
- Barre de progression pendant le téléchargement.

### Paramètres

- Canal de mise à jour.
- Vérification automatique on/off.
- Bouton “Vérifier maintenant”.
- Affichage de la version actuelle et de la dernière version connue.

---

## 17.10 CI/CD

Voir Volume 20 pour le workflow de publication.

Points clés :
- La CI génère `latest.yml`, `latest-mac.yml`, `latest-linux.yml`.
- La CI upload `latest.json` comme asset.
- La CI publie la release en pré-release pour beta/alpha, release normale pour stable.

---

## ✅ Critères d’acceptation de l’auto-update

- [ ] L’application vérifie les mises à jour au démarrage.
- [ ] L’utilisateur est notifié quand une mise à jour est disponible.
- [ ] Le téléchargement est vérifié (signature Windows, SHA256).
- [ ] L’installeur est lancé et l’application redémarre.
- [ ] La CI publie `latest.json` avec la release.
- [ ] Les canaux stable/beta/alpha sont supportés.
- [ ] Une mise à jour corrompue ne remplace pas la version actuelle.
- [ ] L’utilisateur peut choisir son canal et désactiver la vérification auto.

---

## 📚 Références Context7

- `/electron-userland/electron-builder` — `electron-updater`, canaux, `latest.yml`, signatures.
