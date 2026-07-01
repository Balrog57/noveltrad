# Volume 4 — Interface utilisateur

## 4.1 Principes de design

- **Minimalisme fonctionnel.** Un seul bouton visible pour l’action principale.
- **Progressive disclosure.** Les options avancées sont masquées derrière des panneaux dépliables.
- **Feedback immédiat.** Chaque action longue affiche une barre de progression et des logs.
- **Dark mode par défaut.** Clair disponible via Paramètres.
- **Accessibilité.** Contraste WCAG AA, navigation clavier, labels ARIA.

## 4.2 Architecture UI

### Stack technique

- **Vue 3** avec `<script setup lang="ts">`.
- **Vue Router** pour la navigation entre écrans.
- **Pinia** pour la gestion d’état globale.
- **CSS variables** pour les tokens de design (pas de librairie CSS imposée ; utilisation possible de Tailwind ou d’un CSS maison).
- **IPC** via `window.novelTradAPI` exposé dans le preload script.

### Organisation des stores Pinia

```typescript
// stores/project.ts
export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProject: null as Project | null,
    chapters: [] as Chapter[],
    isLoading: false,
    error: null as string | null
  }),
  getters: {
    hasProject: (state) => state.currentProject !== null,
    sortedChapters: (state) => [...state.chapters].sort((a, b) => a.orderIndex - b.orderIndex)
  },
  actions: {
    async openProject(path: string) {
      this.isLoading = true
      this.error = null
      try {
        this.currentProject = await window.novelTradAPI.openProject(path)
        this.chapters = await window.novelTradAPI.listChapters(this.currentProject.id)
      } catch (err) {
        this.error = err instanceof Error ? err.message : 'Failed to open project'
      } finally {
        this.isLoading = false
      }
    }
  }
})
```

### Stores requis

| Store | Responsabilité |
|-------|----------------|
| `useProjectStore` | Projet courant, chapitres, statut de chargement |
| `useWorkflowStore` | Job actif, étapes, logs, pause/reprise |
| `useLexiconStore` | Entrées lexicales, recherche, import/export |
| `useModelStore` | Providers configurés, modèle actif, fallback |
| `useUiStore` | Thème, sidebar, toasts, modals |
| `useHistoryStore` | Versions, diff sélectionné |

### Cycle de vie des données

1. Le renderer appelle une action Pinia.
2. L’action appelle `window.novelTradAPI.<channel>(payload)`.
3. Le main process exécute et retourne une promesse.
4. Les événements temps réel (`workflow:*`, `log`) mettent à jour les stores via des listeners enregistrés au montage.
5. Les composants se re-render via la réactivité Vue/Pinia.

---

## 4.3 Navigation principale

### Layout applicatif

```text
┌─────────────────────────────────────────────────────────────┐
│  NovelTrad 2.0                              [⚙] [⛶] [✕]    │
├───────────────┬─────────────────────────────────────────────┤
│               │                                             │
│  🏠 Accueil   │          Vue active (router-view)           │
│               │                                             │
│  📁 Projet    │                                             │
│               │                                             │
│  📖 Chapitres │                                             │
│               │                                             │
│  📚 Lexique   │                                             │
│               │                                             │
│  ⚙ Workflow   │                                             │
│               │                                             │
│  🕐 Historique│                                             │
│               │                                             │
│  🔧 Paramètres│                                             │
│               │                                             │
│  🖥 Console    │                                             │
│               │                                             │
└───────────────┴─────────────────────────────────────────────┘
```

### Routes Vue Router

| Route | Écran | Accès |
|-------|-------|-------|
| `/` | Accueil | Toujours |
| `/project/:projectId` | Tableau de bord projet | Projet ouvert |
| `/project/:projectId/chapters` | Liste et édition des chapitres | Projet ouvert |
| `/project/:projectId/chapters/:chapterId` | Éditeur côte à côte | Projet ouvert |
| `/project/:projectId/lexicon` | Lexique | Projet ouvert |
| `/project/:projectId/workflow` | Visualisation du workflow | Projet ouvert |
| `/project/:projectId/history` | Historique des versions | Projet ouvert |
| `/settings` | Paramètres globaux | Toujours |
| `/console` | Logs temps réel | Toujours |

### Règles de navigation

- Si aucun projet n’est ouvert, les routes `/project/*` redirigent vers `/`.
- La sidebar reste visible sur toutes les routes sauf `/` (écran Accueil plein écran).
- Le titre de fenêtre reflète le projet courant : `MonProjet — NovelTrad 2.0`.

---

## 4.4 Écran Accueil

### Objectif

Permettre à l’utilisateur de reprendre rapidement un projet récent ou d’en créer un nouveau.

### Wireframe

```text
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              [Logo NovelTrad 2.0]                           │
│                                                             │
│  Projets récents                                            │
│  ────────────────────────                                   │
│  ● Le Cultivateur Immortel                                  │
│    Dernière ouverture : il y a 2 heures                     │
│  ● Sword Saint Online                                       │
│    Dernière ouverture : hier                                │
│  ● Heavenly Demon Reborn                                    │
│    Dernière ouverture : 2026-06-20                          │
│                                                             │
│  [ + Nouveau projet ]   [ Ouvrir un dossier ]             │
│                                                             │
│  ────────────────────────                                   │
│  Documentation · Paramètres · À propos                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Comportements

- Affiche les 10 derniers projets ouverts (titre, chemin, date d’ouverture).
- Clique sur un projet récent → ouverture + navigation vers `/project/:id`.
- Bouton “Nouveau projet” → ouvre le wizard de création (modal ou route `/new-project`).
- Bouton “Ouvrir un dossier” → boîte de dialogue native Electron, puis vérification de `project.db`.
- Si `project.db` manquant dans le dossier sélectionné : proposition de créer un projet à cet emplacement.

### États

- **Vide** : aucun projet récent → message “Bienvenue ! Créez votre premier projet.”
- **Chargement** : spinner pendant l’ouverture.
- **Erreur** : toast si le projet ne peut pas être ouvert (fichier verrouillé, schéma incompatible).

---

## 4.5 Wizard de création de projet

### Étapes

1. **Métadonnées** : nom, auteur, langue source, langue cible.
2. **Emplacement** : dossier parent, nom du dossier projet.
3. **Récapitulatif** : validation + bouton Créer.

### Validation

- Nom non vide, ≤ 100 caractères.
- Dossier parent existant et accessible en écriture.
- Le dossier projet n’existe pas encore (ou est vide).

### Sortie

- Création via `window.novelTradAPI.createProject(config)`.
- Navigation automatique vers `/project/:projectId`.

---

## 4.6 Écran Projet (tableau de bord)

### Contenu

- **En-tête** : titre, auteur, langues source/cible, date de création.
- **Statistiques** :
  - Nombre de chapitres.
  - Nombre de paragraphes traduits / total.
  - Nombre de mots source / cible.
  - Temps de traduction total.
  - Score qualité moyen.
- **Dernier workflow** : statut, date, qualité.
- **Actions rapides** :
  - Traduire le chapitre actif.
  - Ouvrir le lexique.
  - Importer un chapitre.
  - Exporter le projet.

### Composants

- `NtStatCard` : carte statistique avec icône, valeur, label.
- `NtRecentJobList` : liste des derniers jobs avec statut coloré.
- `NtQuickActions` : grille de boutons d’action.

---

## 4.7 Écran Chapitres

### Layout

```text
┌─────────────────────────────────────────────────────────────┐
│  Chapitres                                [ + Importer ]     │
├───────────────┬─────────────────────────────────────────────┤
│ Chapitre 1    │  Source                     Traduction      │
│ Chapitre 2    │  ─────────────────────────────────────────  │
│ Chapitre 3  ● │  Texte source  │  Texte traduit            │
│               │  (lecture seule)│  (éditable)                │
│               │                 │                            │
│               │                 │                            │
│               │  [ Traduire ]   [ Vérifier ] [ Exporter ]   │
└───────────────┴─────────────────────────────────────────────┘
```

### Liste des chapitres

- Colonne de gauche : liste scrollable.
- Statuts visuels :
  - 🔵 Non traduit
  - 🟡 En cours
  - 🟢 Terminé
  - 🔴 Erreur
- Clic droit : menu contextuel (Traduire, Exporter, Voir historique, Supprimer).

### Éditeur côte à côte

- **Panneau source** : texte source en lecture seule, numérotation des paragraphes.
- **Panneau traduction** : éditable, avec undo/redo natif du navigateur.
- **Sous 1024 px** : bascule en onglets “Source / Traduction”.
- **Actions** :
  - Traduire ce chapitre.
  - Vérifier (lance cohérence rapide).
  - Exporter.
  - Voir historique.

### États

- **Aucun chapitre** : bouton “Importer un chapitre” en plein écran.
- **Chapitre sélectionné** : éditeur affiché.
- **Workflow en cours sur ce chapitre** : overlay de progression non bloquant.

---

## 4.8 Écran Lexique

### Layout

- **Barre d’outils** : recherche, filtres par catégorie, import/export, ajouter.
- **Table** : terme, traduction, catégorie, priorité, verrouillage.
- **Panneau d’édition** : formulaire complet à droite ou dans une modal.

### Tableau

| Colonne | Description |
|---------|-------------|
| Terme | Source |
| Traduction | Cible |
| Catégorie | Personnage, secte, objet, etc. |
| Priorité | 0–10 |
| Verrou | 🔒 si `locked` |
| Alias | Aperçu des alias |

### Formulaire d’édition

Champs :
- Terme (obligatoire)
- Traduction (obligatoire)
- Catégorie (select)
- Genre (select optionnel)
- Alias (liste dynamique)
- Description (textarea)
- Notes (textarea)
- Priorité (slider 0–10)
- Verrouillage (toggle)
- Prononciation (optionnel)

### Actions

- Ajouter une entrée.
- Dupliquer.
- Fusionner deux entrées (résolution de conflit).
- Importer CSV/JSON/TSV.
- Exporter CSV/JSON/TSV.

---

## 4.9 Écran Workflow

### Objectif

Visualiser l’état d’avancement du workflow et permettre les interventions utilisateur.

### Composants

- **Pipeline graphique** : étapes en verticale avec icônes d’état.
  - ⏳ En attente
  - 🔄 En cours
  - ✅ Terminé
  - ⚠️ Warning
  - ❌ Échec
  - ⏭️ Sautée
- **Détail de l’étape active** : nom, modèle utilisé, tokens, durée, message.
- **Logs temps réel** : console filtrable par niveau.
- **Actions** : pause, reprendre, annuler, relancer étape, relancer depuis.

### Interactions

- Clic sur une étape terminée : affichage du snapshot entrée/sortie.
- Clic sur une étape en échec : formulaire de correction (modifier lexique, prompt, modèle).

---

## 4.10 Écran Historique

### Layout

- Liste des versions à gauche (numéro, date, score qualité).
- Diff côte à côte à droite.
- Bouton “Restaurer cette version”.

### Diff viewer

- `NtDiffViewer` : affiche ajouts en vert, suppressions en rouge, modifications en jaune.
- Niveau paragraphe par défaut.
- Option “afficher au niveau ligne”.

---

## 4.11 Écran Paramètres

### Sections

1. **IA**
   - Provider actif.
   - Modèle par défaut.
   - Modèle rapide (pré-traduction).
   - Clé API.
   - Provider de fallback.
   - Bouton “Tester la connexion”.
2. **Workflow**
   - Activer/désactiver des étapes.
   - Modèle par étape.
   - Seuil qualité minimum.
   - Nombre max de retries.
3. **Langues**
   - Langue source par défaut.
   - Langue cible par défaut.
   - Dossier de projets par défaut.
4. **Interface**
   - Thème (dark / light / système).
   - Langue UI (fr, en).
   - Taille de police éditeur.
5. **Avancé**
   - Chemin des logs.
   - Niveau de log.
   - Réinitialisation des préférences.
   - Relancer le wizard de premier lancement.

---

## 4.12 Écran Console

### Contenu

- Logs temps réel du main process.
- Filtres par niveau : debug, info, warn, error.
- Recherche textuelle.
- Bouton “Exporter les logs”.
- Bouton “Vider”.

### Comportement

- Les logs arrivent via IPC `log`.
- Affichage avec coloration par niveau.
- Ligne sélectionnable pour copier.

---

## 4.13 Composants réutilisables

### Liste complète

| Composant | Usage |
|-----------|-------|
| `NtButton` | Bouton primaire/secondaire/tertiaire avec états loading/disabled |
| `NtInput` | Input texte avec label, erreur, icône |
| `NtSelect` | Select native stylisé |
| `NtTextarea` | Textarea redimensionnable |
| `NtCard` | Conteneur avec en-tête |
| `NtSidebar` | Navigation latérale |
| `NtProgressBar` | Barre de progression avec pourcentage |
| `NtLogViewer` | Affichage scrollable de logs |
| `NtDiffViewer` | Diff côte à côte |
| `NtToast` | Notification temporaire |
| `NtModal` | Modal avec overlay, focus trap |
| `NtEmptyState` | Écran vide avec icône + action |
| `NtBadge` | Badge de statut |
| `NtTooltip` | Infobulle |
| `NtSplitPane` | Séparateur draggable pour éditeur côte à côte |

### Spécifications par composant

#### `NtButton`

```vue
<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md'
})
</script>
```

- `loading=true` : spinner + texte inchangé, événement click désactivé.
- `disabled=true` : opacité réduite, curseur not-allowed.

#### `NtModal`

- Focus trap (Tab boucle dans la modal).
- Escape ferme la modal.
- Click sur overlay ferme.
- Animation 150 ms.
- Taille configurable (`sm`, `md`, `lg`, `fullscreen`).

#### `NtSplitPane`

- Utilise une barre draggable entre deux panneaux.
- Persiste le ratio dans `settings`.
- Sous 1024 px : remplacé par des onglets.

---

## 4.14 Dark mode / Light mode

### Implémentation

- Classe CSS `theme-dark` ou `theme-light` sur `<html>`.
- Variables CSS redéfinies selon le thème.
- Préférence stockée dans `settings` (`theme: 'dark' | 'light' | 'system'`).
- Mode “système” : écoute `matchMedia('(prefers-color-scheme: dark)')`.

### Exemple

```css
:root {
  --bg-primary: #0f172a;
  --text-primary: #f8fafc;
}

.theme-light {
  --bg-primary: #ffffff;
  --text-primary: #0f172a;
}
```

---

## 4.15 Accessibilité

### Navigation clavier

- `Tab` parcourt les éléments interactifs dans l’ordre visuel.
- `Enter` active le bouton ou le lien focalisé.
- `Escape` ferme les modals, les menus, annule les actions en cours.
- Raccourcis globaux (optionnels) :
  - `Ctrl/Cmd + N` : nouveau projet.
  - `Ctrl/Cmd + O` : ouvrir un projet.
  - `Ctrl/Cmd + Shift + T` : traduire le chapitre actif.

### ARIA

- Icônes décoratives masquées avec `aria-hidden="true"`.
- Boutons avec icône seule ont un `aria-label` explicite.
- Les notifications utilisent `role="status"` ou `role="alert"`.
- Les modals utilisent `role="dialog"` et `aria-modal="true"`.

### Contraste

- Texte principal sur fond principal : ratio ≥ 4.5:1.
- Texte grand (titres) : ratio ≥ 3:1.
- Éléments interactifs : ratio ≥ 3:1.

---

## 4.16 Responsive

### Breakpoints

| Breakpoint | Largeur | Adaptation |
|------------|---------|------------|
| `sm` | < 640 px | Non cible prioritaire (desktop) |
| `md` | 640–1024 px | Sidebar rétractable, éditeur en onglets |
| `lg` | > 1024 px | Layout complet sidebar + contenu |

### Comportements

- Sidebar : bouton hamburger en `md`, toujours visible en `lg`.
- Éditeur côte à côte : onglets en `md`, split pane en `lg`.
- Paramètres : une colonne en `md`, deux colonnes en `lg`.

---

## 4.17 Gestion des erreurs et états vides

### Patterns d’état vide

| Écran | État vide | Action principale |
|-------|-----------|-------------------|
| Accueil | Aucun projet récent | “Créer un projet” |
| Chapitres | Aucun chapitre importé | “Importer un chapitre” |
| Lexique | Lexique vide | “Ajouter une entrée” |
| Workflow | Aucun job exécuté | “Traduire un chapitre” |
| Historique | Aucune version | “Traduire un chapitre” |
| Console | Aucun log | Message informatif |

### Toasts

- `NtToast` affiche un message temporaire.
- Types : success, info, warning, error.
- Durée : 4 s (sauf error : persiste jusqu’à fermeture manuelle).
- Position : haut à droite.

---

## 4.18 Parcours utilisateur critiques

### Parcours 1 — Premier lancement

```text
Lancer l’application
    ↓
Wizard de bienvenue
    ↓
Détection Ollama → installation si besoin
    ↓
Téléchargement modèle par défaut
    ↓
Configuration langues
    ↓
Écran Accueil
    ↓
Créer un projet
    ↓
Importer un chapitre
    ↓
Traduire le chapitre
    ↓
Exporter
```

### Parcours 2 — Reprise d’un projet

```text
Écran Accueil
    ↓
Cliquer sur projet récent
    ↓
Tableau de bord projet
    ↓
Ouvrir Chapitres
    ↓
Sélectionner un chapitre
    ↓
Cliquer “Traduire”
    ↓
Suivre le workflow
    ↓
Vérifier le score qualité
    ↓
Exporter
```

### Parcours 3 — Correction manuelle

```text
Workflow en pause sur étape Grammaire
    ↓
Ouvrir l’étape en échec
    ↓
Modifier le texte dans l’éditeur
    ↓
Relancer l’étape
    ↓
Continuer le workflow
```

---

## ✅ Critères d’acceptation de l’UI

- [ ] Les 8 écrans principaux sont routés avec Vue Router.
- [ ] Le thème sombre couvre tous les composants.
- [ ] La navigation clavier fonctionne (Tab, Enter, Escape).
- [ ] Les actions longues affichent une barre de progression.
- [ ] Les erreurs sont affichées dans une notification toast.
- [ ] L’éditeur côte à côte passe en onglets sous 1024 px.
- [ ] Les états vides ont une action principale claire.
- [ ] Chaque composant réutilisable a une story/tests unitaires.
- [ ] Les stores Pinia sont testés avec des mocks IPC.

---

## 📚 Références Context7

- `/websites/vuejs_guide` — Vue 3 Composition API, composants, accessibilité.
- `/vuejs/router` — Vue Router, navigation programmatique, guards.
- `/vuejs/pinia` — Stores, actions, getters, persistence.
- `/electron/electron` — `contextBridge`, IPC sécurisé, `BrowserWindow`.
