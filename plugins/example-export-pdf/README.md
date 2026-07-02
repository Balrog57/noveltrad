# Export PDF Example — NovelTrad Plugin

Plugin d'exemple pour NovelTrad (SDD Volume 15).

## Installation

1. Copier ce dossier dans le dossier `plugins/` de NovelTrad :
   - Windows : `%APPDATA%/NovelTrad/plugins/`
   - macOS : `~/Library/Application Support/NovelTrad/plugins/`
   - Linux : `~/.config/NovelTrad/plugins/`
2. Redémarrer NovelTrad.
3. Aller dans Paramètres → Plugins pour activer le plugin.

## Fonctionnalité

Ajoute un format d'export `pdf` à l'ExportEngine de NovelTrad.

## Structure

```
example-export-pdf/
├── manifest.json    # Métadonnées du plugin (id, version, permissions)
├── index.mjs        # Point d'entrée ESM pré-compilé
└── README.md        # Cette documentation
```

## Dépendances

Aucune. Plugin autonome.

## Permissions

- `fs-write` : nécessaire pour écrire le fichier PDF exporté.
