# Volume 20 — CI/CD

## 20.1 Stratégie globale

- **CI** : lint, tests unitaires, tests E2E, build à chaque push/PR.
- **Release** : build + packaging + publication GitHub Releases sur les tags semver.
- **Plateformes** : Windows (prioritaire), macOS, Linux.
- **Cache** : dépendances npm et outputs de build.

---

## 20.2 Workflow CI (`ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Unit tests
        run: npm run test:unit

      - name: Type check
        run: npm run type-check

      - name: Build
        run: npm run build

  e2e:
    runs-on: windows-latest
    needs: lint-and-test
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload E2E results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-results
          path: |
            test-results/
            playwright-report/
```

### Explications

- `concurrency` : annule les anciens runs sur la même branche/PR.
- `actions/setup-node@v4` + `cache: npm` : cache les dépendances.
- E2E sur Windows car NovelTrad cible principalement Windows.
- Upload des résultats E2E uniquement en cas d’échec.

---

## 20.3 Workflow Release (`release.yml`)

```yaml
name: Release

on:
  push:
    tags:
      - 'v[0-9]+.[0-9]+.[0-9]+'
      - 'v[0-9]+.[0-9]+.[0-9]+-*'

permissions:
  contents: write

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, macos-latest, ubuntu-latest]

    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm

      - name: Install dependencies
        run: npm ci

      - name: Verify tag matches source version
        shell: pwsh
        run: |
          $tag = "${{ github.ref_name }}".TrimStart('v')
          $src = node -p "require('./package.json').version"
          if ($tag -ne $src) {
            Write-Error "Tag $tag does not match package.json version $src"
            exit 1
          }
          Write-Host "Tag matches version: $tag"

      - name: Build and package
        run: npm run dist
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.os }}
          path: |
            dist/*.exe
            dist/*.dmg
            dist/*.AppImage
            dist/*.deb
            dist/latest*.yml
            dist/latest*.json

  release:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Create or update GitHub release
        shell: pwsh
        run: |
          $tag = "${{ github.ref_name }}"
          $pre = if ($tag -match '-(alpha|beta|rc)') { '--prerelease' } else { '' }

          # Créer la release si elle n'existe pas
          gh release create $tag $pre --title $tag --notes-from-tag --draft || true

          # Upload latest.json
          if (Test-Path "latest.json") {
            gh release upload $tag latest.json --clobber
          }

          # Upload artifacts par OS
          Get-ChildItem artifacts -Recurse -File | ForEach-Object {
            gh release upload $tag $_.FullName --clobber
          }
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Explications

- Matrice OS : build Windows, macOS, Linux.
- `fail-fast: false` : si une plateforme échoue, les autres continuent.
- Vérification tag-vs-version avant build.
- Publie en `draft` pour permettre une vérification manuelle avant publication.
- Détecte automatiquement les pré-releases via regex sur le tag.

---

## 20.4 Code signing

### Windows (Authenticode)

```yaml
      - name: Build and package
        run: npm run dist
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CSC_LINK: ${{ secrets.CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.CSC_KEY_PASSWORD }}
```

### macOS

```yaml
      - name: Build and package
        run: npm run dist
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
          CSC_LINK: ${{ secrets.MAC_CSC_LINK }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CSC_KEY_PASSWORD }}
```

### Fallback sans certificat

- Si les secrets ne sont pas définis, `electron-builder` produit des binaires non signés.
- L’auto-update fonctionne toujours mais affiche des avertissements de sécurité.

---

### Variables et secrets GitHub Actions

Les valeurs sensibles sont configurées dans **Settings → Secrets and variables → Actions** du dépôt GitHub.

| Secret / Variable | Usage | Obligatoire |
|---|---|---|
| `CSC_LINK` | Certificat Authenticode Windows encodé en base64 (fichier `.p12` ou `.pfx`) | Non (signé si présent) |
| `CSC_KEY_PASSWORD` | Mot de passe du certificat Windows | Si `CSC_LINK` est défini |
| `MAC_CSC_LINK` | Certificat Apple Developer ID (`.p12`) | Non |
| `MAC_CSC_KEY_PASSWORD` | Mot de passe du certificat macOS | Si `MAC_CSC_LINK` est défini |
| `APPLE_ID` | Identifiant Apple pour la notarisation | Recommandé pour macOS |
| `APPLE_APP_SPECIFIC_PASSWORD` | Mot de passe d'application pour la notarisation | Si `APPLE_ID` est défini |
| `APPLE_TEAM_ID` | Équipe Apple (si plusieurs teams) | Selon cas |
| `GH_TOKEN` / `GITHUB_TOKEN` | Token pour la création/upload de release | Oui (fourni par GitHub) |

**Bonnes pratiques.**
- Ne jamais stocker les certificats dans le repo ; utiliser des *Repository secrets*.
- Pour les forks ou les builds locaux, `electron-builder` produit automatiquement des binaires non signés si les secrets sont absents.
- Inclure une étape CI de vérification qui affiche `Code signing: enabled`/`disabled` sans révéler les valeurs.

```yaml
      - name: Check code signing configuration
        shell: pwsh
        run: |
          $win = if ($env:CSC_LINK) { 'enabled' } else { 'disabled' }
          $mac = if ($env:MAC_CSC_LINK) { 'enabled' } else { 'disabled' }
          Write-Host "Code signing status: Windows=$win macOS=$mac"
```
## 20.5 Publication des assets

### Fichiers attendus par release

| Fichier | Source | Usage |
|---------|--------|-------|
| `Setup_NovelTrad-X.Y.Z.exe` | `electron-builder` Windows | Installeur Windows |
| `NovelTrad-X.Y.Z.dmg` | `electron-builder` macOS | Installeur macOS |
| `NovelTrad-X.Y.Z.AppImage` | `electron-builder` Linux | Installeur Linux |
| `latest.yml` | `electron-builder` Windows | Auto-update Windows |
| `latest-mac.yml` | `electron-builder` macOS | Auto-update macOS |
| `latest-linux.yml` | `electron-builder` Linux | Auto-update Linux |
| `latest.json` | repo root | Manifeste enrichi |

### latest.json

Voir Volume 17. Le fichier doit être mis à jour manuellement avant chaque tag pour refléter :
- version,
- URL de téléchargement,
- SHA256 de l’installeur Windows.

---

### Génération et upload de `latest.json` en CI

`latest.json` n'est pas produit par `electron-builder`. Il est généré par un script CI à partir de l'installeur Windows et uploadé comme asset de release.

#### Étape 1 — Générer `latest.json` dans le job Windows

```yaml
      - name: Generate latest.json (Windows)
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          $tag = "${{ github.ref_name }}".TrimStart('v')
          $exe = Get-ChildItem dist/*.exe | Select-Object -First 1
          if (!$exe) { Write-Error "No Windows installer found"; exit 1 }
          npx tsx scripts/generate-latest-json.ts `
            --version $tag `
            --installer $exe.FullName `
            --output latest.json
          Get-Content latest.json | ConvertFrom-Json | Write-Host
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Étape 2 — Collecte cross-plateforme

Chaque OS upload ses artefacts via `actions/upload-artifact@v4`. Le job `release` les télécharge avec `actions/download-artifact@v4` et crée la release GitHub.

#### Étape 3 — Upload de `latest.json` comme asset

```yaml
      - name: Upload latest.json to release
        shell: pwsh
        run: |
          $tag = "${{ github.ref_name }}"
          if (Test-Path latest.json) {
            gh release upload $tag latest.json --clobber
          }
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Points de vigilance.**
- `latest.json` doit toujours correspondre au tag en cours ; l'étape de vérification tag-vs-version bloque sinon.
- L'upload utilise `--clobber` pour permettre les re-runs sans échec.
- Les fichiers `latest.yml`, `latest-mac.yml`, `latest-linux.yml` sont générés par `electron-builder` et uploadés en même temps.
## 20.6 Tests en CI

### Unit tests

- Vitest, couverture minimale 70 %.
- Exécution sur Ubuntu pour la rapidité.

### E2E tests

- Playwright, parcours critiques :
  1. Premier lancement + wizard + création projet.
  2. Import chapitre + lancer workflow + export.
  3. Changer provider IA + tester connexion.
- Exécution sur Windows car c’est la cible principale.

### Lint et type check

- ESLint + Prettier.
- `vue-tsc` pour le type checking Vue/TypeScript.

---

## 20.7 Cache et performance

### Cache npm

- Fourni par `actions/setup-node@v4` avec `cache: npm`.

### Cache build

```yaml
      - uses: actions/cache@v4
        with:
          path: |
            node_modules/.vite
            dist
          key: ${{ runner.os }}-build-${{ hashFiles('package-lock.json') }}-${{ github.sha }}
          restore-keys: |
            ${{ runner.os }}-build-${{ hashFiles('package-lock.json') }}
```

---

## 20.8 Gestion des échecs

### CI

- Un échec de lint ou de test bloque la fusion.
- Les E2E peuvent être marqués `continue-on-error: true` temporairement si instables.

### Release

- Si la vérification tag-vs-version échoue, le build s’arrête.
- Si une plateforme échoue, les autres publient quand même (grâce à `fail-fast: false`).
- La release est créée en draft pour permettre une vérification manuelle.

---

## ✅ Critères d’acceptation CI/CD

- [ ] La CI exécute lint, tests, build à chaque push/PR.
- [ ] La release se déclenche uniquement sur les tags semver stables ou pré-release.
- [ ] La vérification tag-vs-version bloque les releases incohérentes.
- [ ] Les artefacts des 3 plateformes sont uploadés.
- [ ] `latest.json` est uploadé comme asset.
- [ ] La release est créée en draft pour vérification.
- [ ] Les tests E2E couvrent les parcours critiques.
- 
- [ ] Les secrets de code signing sont documentés et configurables via les *Repository secrets* GitHub.
- [ ] latest.json est généré en CI et uploadé comme asset de release.
- [ ] Les versions d'actions GitHub Actions utilisées sont 4 (pas 5/6).

---

## 📚 Références Context7

- `/websites/github_en_actions` — GitHub Actions syntaxe et bonnes pratiques.
- `/actions/checkout` — Checkout v4.
- `/actions/cache` — Cache v4.
- `/actions/upload-artifact` — Upload artifacts v4.

