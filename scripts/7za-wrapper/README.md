# 7za wrapper (Windows)

## Problème

`electron-builder` télécharge `winCodeSign-2.6.0.7z` puis l'extrait via
`7za.exe`. Cette archive contient 2 **liens symboliques macOS**
(`darwin/10.12/lib/libcrypto.dylib`, `libssl.dylib`) que `7za` ne peut pas
créer sous Windows sans le privilège *Créer des liens symboliques* (admin ou
Mode développeur). `7za` sort alors en **exit code 2** (warning), que le
binaire Go `app-builder` d'electron-builder traite comme **fatal** → le build
Windows échoue systématiquement.

Comme les builds NovelTrad sont **non signés**, ces symlinks macOS sont
inutiles — ils ne servent qu'à la signature des binaires macOS.

## Solution

Un wrapper Go (`7za.exe`) délègue au vrai `7za-real.exe` et **masque l'exit
code 2** :

```go
// extrait de main.go
if code == 2 { os.Exit(0) }  // warning symlink → on continue
os.Exit(code)
```

## Fichiers

- `main.go` — source Go du wrapper
- `bin/7za-wrapper-x64.exe` — binaire précompilé (Windows x64) committé
- `install.cjs` — script post-install Node (idempotent)

## Installation automatique

Le `postinstall` de `apps/desktop/package.json` exécute `install.cjs` après
chaque `npm install`. Effet :

1. Renomme `node_modules/7zip-bin/win/x64/7za.exe` → `7za-real.exe`
2. Copie le wrapper précompilé à la place de `7za.exe`

Le script est **idempotent** (no-op si déjà installé) et **no-op** hors Windows
ou si `7zip-bin` n'est pas présent.

## Recompiler le wrapper (si besoin)

```bash
cd scripts/7za-wrapper
CGO_ENABLED=0 GOOS=windows GOARCH=amd64 \
  go build -ldflags="-s -w" -o bin/7za-wrapper-x64.exe main.go
```

## Alternative (plus propre, pas de wrapper)

Activer le **Mode développeur Windows** :
*Settings → For developers → Developer Mode: On*

Cela autorise la création de symlinks sans admin, et le wrapper devient
superflu. On peut alors retirer le `postinstall` si tous les postes de build
ont le Mode développeur activé.
