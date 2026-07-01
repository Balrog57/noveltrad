# Volume 23 — Système de design

## 23.1 Palette

### Dark mode (par défaut)

| Token | Valeur | Usage |
|-------|--------|-------|
| `--bg-primary` | `#0f172a` | Fond principal |
| `--bg-secondary` | `#1e293b` | Panneaux, sidebar |
| `--bg-tertiary` | `#334155` | Inputs, cartes |
| `--text-primary` | `#f8fafc` | Texte principal |
| `--text-secondary` | `#94a3b8` | Texte secondaire |
| `--accent` | `#38bdf8` | Boutons primaires |
| `--accent-hover` | `#0ea5e9` | Hover |
| `--success` | `#22c55e` | Succès |
| `--warning` | `#f59e0b` | Avertissement |
| `--error` | `#ef4444` | Erreur |

### Light mode

- Fonds inversés (`#ffffff`, `#f8fafc`, `#e2e8f0`).
- Texte principal `#0f172a`.

### Utilisation

```css
:root {
  --bg-primary: #0f172a;
  --text-primary: #f8fafc;
}

.theme-light {
  --bg-primary: #ffffff;
  --text-primary: #0f172a;
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}
```

---

## 23.2 Typographie

### Polices

| Usage | Police | Fallback |
|-------|--------|----------|
| UI | Inter | system-ui, sans-serif |
| Éditeur code | JetBrains Mono | monospace |
| Texte chinois | Source Han Serif | serif |

### Échelle

| Niveau | Taille | Poids | Usage |
|--------|--------|-------|-------|
| Titre 1 | 24 px | 700 | Titres de page |
| Titre 2 | 20 px | 600 | Sections |
| Titre 3 | 16 px | 600 | Sous-sections |
| Corps | 14 px | 400 | Texte standard |
| Petit | 12 px | 400 | Légendes, méta |
| Code | 13 px | 400 | Logs, code |

---

## 23.3 Composants

### Spécifications par composant

#### `NtButton`

| État | Style |
|------|-------|
| Default | `bg-accent`, `text-white`, `rounded-md`, `px-4 py-2` |
| Hover | `bg-accent-hover` |
| Disabled | `opacity-50`, `cursor-not-allowed` |
| Loading | Spinner 16 px + texte inchangé |

#### `NtInput`

| État | Style |
|------|-------|
| Default | `bg-bg-tertiary`, `border border-transparent`, `rounded-md`, `px-3 py-2` |
| Focus | `border-accent`, `ring-1 ring-accent` |
| Error | `border-error`, `text-error` |
| Disabled | `opacity-50` |

#### `NtSelect`

- Même base que `NtInput`.
- Flèche à droite.
- Options dans un menu overlay.

#### `NtCard`

- `bg-bg-secondary`, `rounded-lg`, `p-4`, `shadow-sm`.
- Optionnel : en-tête avec titre et actions.

#### `NtSidebar`

- Largeur 240 px.
- `bg-bg-secondary`.
- Élément actif : `bg-bg-tertiary`, `border-l-4 border-accent`.

#### `NtProgressBar`

- Hauteur 8 px.
- `bg-bg-tertiary` track, `bg-accent` fill.
- Pourcentage affiché à droite.

#### `NtLogViewer`

- Font monospace.
- Coloration par niveau.
- Scroll auto optionnel.

#### `NtDiffViewer`

- Côte à côte ou unifié.
- Ajouts : fond vert.
- Suppressions : fond rouge.
- Modifications : fond jaune.

#### `NtToast`

- Position haut droite.
- Durée 4 s (error persiste).
- Types : success, info, warning, error.

#### `NtModal`

- Overlay `bg-black/50`.
- Contenu centré.
- Focus trap.
- Escape pour fermer.

---

## 23.4 Animations

- Transitions : 150 ms ease.
- Barres de progression animées.
- Toast slide-in depuis le haut à droite.
- Modal fade-in + scale.

---

## 23.5 Accessibilité

- Contraste minimum 4.5:1 pour le texte.
- Focus visible sur tous les éléments interactifs.
- Labels ARIA pour les icônes.
- Raccourcis clavier documentés.

### Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl/Cmd + N` | Nouveau projet |
| `Ctrl/Cmd + O` | Ouvrir un projet |
| `Ctrl/Cmd + Shift + T` | Traduire le chapitre actif |
| `Escape` | Fermer modal/annuler action |

---

## 23.6 Responsive

### Breakpoints

| Breakpoint | Largeur | Adaptation |
|------------|---------|------------|
| `md` | 640–1024 px | Sidebar rétractable, éditeur en onglets |
| `lg` | > 1024 px | Layout complet |

---

## 23.7 Icônes

- Librairie : `@heroicons/vue` ou `lucide-vue-next`.
- Taille par défaut : 20 px.
- Couleur : `currentColor`.

---

## ✅ Critères d’acceptation du design system

- [ ] Les tokens CSS sont centralisés.
- [ ] Tous les composants réutilisables sont documentés avec leurs états.
- [ ] Le contraste respecte WCAG AA.
- [ ] Le mode sombre est complet.
- [ ] Les animations ne bloquent pas les interactions.
- [ ] Les icônes sont cohérentes.

---

## 📚 Références Context7

- `/websites/vuejs_guide` — Composants Vue 3, transitions.
