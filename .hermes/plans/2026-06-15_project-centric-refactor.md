# Refactor Project-Centric — Architecture centrée sur le projet

> **Pour Hermes:** Utiliser le skill `plan` pour guider l'implémentation. Faire valider chaque phase avant de coder.

**Objectif :** Restructurer NovelTrad pour que le **Projet** devienne le concept central.
L'onglet 1 devient "Projects" — créer/modifier/supprimer des projets (nom + dossier unique qui sert
de répertoire de travail ET de destination). Les fichiers à traduire sont ajoutés dans l'onglet 2 (Pipeline)
depuis n'importe où sur le disque. Les onglets Pipeline, Files et Glossary dépendent tous du projet
actif. Basculer de projet change tout le contexte.

**Architecture :** PyQt6 GUI avec FastAPI backend. L'état "projet actif" est partagé via le backend (StateStore) et le GUI y réagit. Les routes API existantes sont étendues avec un paramètre `project_id` et de nouvelles routes sont ajoutées pour la gestion des projets (CRUD).

**Stack technique :** Python 3.12, PyQt6, FastAPI, SQLite (StateStore), LanceDB (vecteurs)

---

## État actuel

```
Sidebar: [Translate] [Projects] [Glossaries] [Files] [Settings]

TranslateTab: Select → Pipeline → Review (tout-en-un, envoie vers /projects)
ProjectsTab:  Liste statique des projets passés (lecture seule)
GlossariesTab: Lexique global (/lexicon)
FilesTab:     Chunks globaux (/chunks)
SettingsTab:  Configuration app
```

## État cible

```
Sidebar: [Projects] [Pipeline] [Glossary] [Files] [Settings]
              │           │           │          │
              └───────────┴───────────┴──────────┘
                     Tous scopés au projet actif

ProjectsTab (onglet 1):
  - Historique des 10 derniers projets (liste rapide, dernier utilisé en haut)
  - Créer un nouveau projet → juste un nom + un dossier de travail (c'est tout)
  - Charger un dossier de projet existant (browse → ouvre un dossier)
  - Supprimer un projet (avec confirmation)
  - Renommer un projet
  - Activer un projet → met à jour Pipeline/Files/Glossary

PipelineTab (ex-Translate, onglet 2):
  - Affiche le nom du projet actif en header
  - Drop zone pour charger les fichiers À TRADUIRE (depuis n'importe où)
  - Lance / Arrête / Reprend la traduction
  - Retour visuel sur la progression de CHAQUE fichier (barre + statut)
  - Contrôles : Pause / Resume / Stop par fichier ou global

FilesTab (onglet 4):
  - Explorateur de fichiers du dossier projet
  - Affiche TOUS les fichiers : source, en cours, terminés, erreurs
  - Chaque fichier a un statut visible (working, done, error, queued…)
  - Double-clic → ouvre le fichier pour APERÇU (vérifier la trad)
  - Possibilité de modifier/corriger un fichier directement
  - Filtre par statut

GlossaryTab (onglet 3):
  - Affiche le glossaire DU PROJET ACTIF (auto-construit pendant la trad)
  - Édition inline : voir et corriger les entrées
  - Ajout / suppression de termes
  - Import/Export JSON

SettingsTab (onglet 5): inchangé
```

---

## Phase 1 — Backend: Project CRUD + Active Project State

### Task 1.1: Ajouter les routes CRUD projet

**Objectif :** Permettre de créer, lister, modifier, supprimer des projets via l'API.

**Fichiers :**
- Modifier : `src/backend/routes/projects.py`
- Modifier : `src/backend/routes/schemas.py`

**Routes à ajouter :**

```python
# GET /projects — déjà existant, à étendre avec plus de métadonnées
# POST /projects — déjà existant (crée + lance traduction), à conserver
# PUT /projects/{project_id} — NOUVEAU : modifier nom, dossiers
# DELETE /projects/{project_id} — NOUVEAU : supprimer un projet
# GET /projects/{project_id} — NOUVEAU : détails d'un projet
```

**Schéma ProjectUpdateRequest :**
```python
class ProjectUpdateRequest(BaseModel):
    name: str | None = None
    project_dir: str | None = None    # dossier de travail
```

**Schéma ProjectCreateRequest (mis à jour) :**
```python
class ProjectCreateRequest(BaseModel):
    name: str                          # nom du projet
    project_dir: str                   # dossier unique (travail + destination)
    # Pas de langues à la création — c'est minimal
```

**Étape 1 : Écrire le test**

```python
# tests/test_project_crud.py
def test_create_and_update_project():
    client = TestClient(create_app(db_path=":memory:", vector_dir=tmp))
    # Créer
    res = client.post("/projects", json={"name": "Test", "project_dir": "/tmp/test"})
    assert res.status_code == 200
    pid = res.json()["project_id"]
    # Modifier
    res = client.put(f"/projects/{pid}", json={"name": "Renamed"})
    assert res.json()["name"] == "Renamed"
    # Supprimer
    res = client.delete(f"/projects/{pid}")
    assert res.json()["ok"] is True
```

**Étape 2 :** `python -m unittest tests.test_project_crud -v` → FAIL

**Étape 3 :** Implémenter les routes PUT/DELETE/GET dans `projects.py`

**Étape 4 :** Tests → PASS

**Étape 5 :** Commit `feat(backend): add project CRUD routes (PUT/DELETE/GET)`

---

### Task 1.2: Ajouter la notion de "projet actif" dans le StateStore

**Objectif :** Le backend maintient quel projet est actif. Les routes Files/Glossary/Pipeline utilisent ce projet actif si aucun `project_id` n'est passé explicitement.

**Fichiers :**
- Modifier : `src/backend/orchestrator/state_store.py`

**Changements :**
```python
# StateStore — nouvelles méthodes
def set_active_project(self, project_id: str) -> None: ...
def get_active_project(self) -> str | None: ...
def clear_active_project(self) -> None: ...
```

Le projet actif est stocké dans la table `state` (clé `active_project_id`).

**Étape 1 :** Écrire le test unitaire sur StateStore
**Étape 2 :** `python -m unittest tests.test_state_store -v` → FAIL
**Étape 3 :** Implémenter les 3 méthodes
**Étape 4 :** Tests → PASS
**Étape 5 :** Commit `feat(store): add active project state methods`

---

### Task 1.3: Route pour changer le projet actif

**Objectif :** `POST /projects/activate/{project_id}` — le GUI appelle cette route pour changer de projet.

**Fichier :** `src/backend/routes/projects.py`

```python
@app.post("/projects/activate/{project_id}")
def activate_project(project_id: str) -> dict[str, Any]:
    deps.store.set_active_project(project_id)
    return {"ok": True, "active_project_id": project_id}
```

**Étape 1 :** Test → FAIL
**Étape 2 :** Implémentation
**Étape 3 :** Test → PASS
**Étape 4 :** Commit `feat(backend): add project activation endpoint`

---

### Task 1.4: Scoper les routes Files/Glossary/Pipeline au projet actif

**Objectif :** Les routes `/chunks`, `/lexicon`, `/pipeline/state` acceptent un paramètre optionnel `project_id`. Si absent, elles utilisent le projet actif du StateStore.

**Fichiers :**
- Modifier : `src/backend/routes/chunks.py`
- Modifier : `src/backend/routes/lexicon.py`
- Modifier : `src/backend/routes/projects.py` (pipeline state)

**Pattern :**
```python
@app.get("/chunks")
def list_chunks(project_id: str | None = None, ...):
    pid = project_id or deps.store.get_active_project()
    if not pid:
        raise HTTPException(400, "No active project")
    return deps.store.list_chunks(project_id=pid, ...)
```

**Étape 1 :** Tests pour chaque route avec `project_id` → FAIL
**Étape 2 :** Implémenter le paramètre optionnel
**Étape 3 :** Tests → PASS
**Étape 4 :** Commit `feat(backend): scope chunks/lexicon/pipeline to active project`

---

## Phase 2 — GUI: ProjectsTab devient le hub central

### Task 2.1: Refactor SIDEBAR_ITEMS — Projects en premier

**Objectif :** Changer l'ordre de la sidebar. Projects devient l'onglet 1.

**Fichier :** `src/gui/main_window.py`

```python
SIDEBAR_ITEMS = (
    ("projects", "Projects"),     # ← passe en premier
    ("pipeline", "Pipeline"),     # ← renommé (ex-Translate)
    ("glossary", "Glossary"),     # ← renommé
    ("files", "Files"),
    ("settings", "Settings"),
)
```

Les clés changent : `translate` → `pipeline`, `glossaries` → `glossary`.

**Étape 1 :** Modifier SIDEBAR_ITEMS
**Étape 2 :** Renommer les attributs dans MainWindow (`self._translate_tab` → `self._pipeline_tab`, `self._glossaries_tab` → `self._glossary_tab`)
**Étape 3 :** `python -m compileall src` → OK
**Étape 4 :** Commit `refactor(gui): reorder sidebar — Projects first, rename tabs`

---

### Task 2.2: Reconstruire ProjectsTab — création/modification/suppression de projets

**Objectif :** Le ProjectsTab devient un vrai gestionnaire de projets avec formulaire de création, liste avec actions, et sélection du projet actif.

**Fichiers :**
- Réécrire : `src/gui/tabs/projects_tab.py`
- Nouveau : `src/gui/dialogs/project_dialog.py` (formulaire création/édition)

**UI du ProjectsTab :**

```
┌──────────────────────────────────────────────────────────┐
│  📁 Projects                                  [+ New] [📂 Open] │
│                                                          │
│  Historique (10 derniers)                                │
│  ┌──────────────────────────────────────────────────────┐│
│  │ 🔵 Renegade Immortal     C:\Novels\Renegade\        ││
│  │    245 fichiers · il y a 2h          [Open] [✏ Rename] [🗑] ││
│  │──────────────────────────────────────────────────────││
│  │ ⚪ A Will Eternal        C:\Novels\awe\              ││
│  │    120 fichiers · hier                [Open] [✏ Rename] [🗑] ││
│  │──────────────────────────────────────────────────────││
│  │ ⚪ Battle Through Heavens C:\Novels\bth\             ││
│  │    89 fichiers · 3j                    [Open] [✏ Rename] [🗑] ││
│  └──────────────────────────────────────────────────────┘│
│                                                          │
│  Projet actif: 🔵 Renegade Immortal                      │
└──────────────────────────────────────────────────────────┘
```

**ProjectDialog (création) — minimal :**
```
┌─────────────────────────────────────┐
│  New Project                    [X] │
│                                     │
│  Name: [Renegade Immortal      ]    │
│  Folder: [C:\Novels\Renegade\] [📂] │
│                                     │
│  [Cancel]  [Create]                 │
└─────────────────────────────────────┘
```

Pas de sélection de langues à la création — c'est fait plus tard si besoin.

**Étape 1 :** Écrire `project_dialog.py` — QDialog minimal : QLineEdit pour nom, QPushButton pour browse dossier, boutons Cancel/Create
**Étape 2 :** Réécrire `projects_tab.py` :
  - Header avec boutons "+ New" et "📂 Open" (charger un dossier existant)
  - Historique des 10 derniers projets dans une QTableWidget
  - Colonnes : Nom, Dossier, Infos (fichiers/modifié), Actions (Open/Rename/Delete)
  - Barre de statut "Projet actif: X"
  - Double-clic = Open (active le projet)
  - Signaux : `projectActivated`, `projectCreated`, `projectDeleted`
**Étape 3 :** Connecter les signaux dans MainWindow
**Étape 4 :** `python -m compileall src` → OK
**Étape 5 :** Commit `feat(gui): rebuild ProjectsTab with CRUD + project activation`

---

### Task 2.3: Intégrer la sélection de projet dans MainWindow

**Objectif :** Quand l'utilisateur active un projet (Open), le GUI change de projet actif côté backend et rafraîchit les onglets Pipeline/Files/Glossary.

**Fichier :** `src/gui/main_window.py`

```python
def _on_project_activated(self, proj: dict[str, Any]) -> None:
    pid = proj["project_id"]
    # 1. POST /projects/activate/{pid}
    self._client.post(f"/projects/activate/{pid}")
    # 2. Rafraîchir tous les onglets dépendants
    self._pipeline_tab.set_project(proj)
    self._files_tab.set_project_id(pid)
    self._glossary_tab.set_project_id(pid)
    # 3. Mettre à jour le badge
    self.statusBar().showMessage(f"Projet actif: {proj.get('name', pid[:8])}")
```

**Étape 1 :** Ajouter les méthodes `set_project()` / `set_project_id()` dans PipelineTab, FilesTab, GlossaryTab
**Étape 2 :** Implémenter `_on_project_activated` dans MainWindow
**Étape 3 :** Commit `feat(gui): wire project activation to all dependent tabs`

---

## Phase 3 — GUI: PipelineTab (ex-TranslateTab) scopé au projet

### Task 3.1: Renommer TranslateTab → PipelineTab

**Objectif :** Renommage + header qui affiche le projet actif.

**Fichier :** `src/gui/tabs/pipeline_tab.py` (ex `translate_tab.py`)

**Changements :**
- La classe `TranslateTab` devient `PipelineTab`
- Le header affiche le nom du projet actif : `"🔵 Renegade Immortal — Pipeline"`
- `set_project(proj)` stocke le projet et rafraîchit l'affichage
- Le bouton "Start Translation" ajoute les fichiers AU PROJET (pas besoin de spécifier project_dir)
- Les fichiers ajoutés vont dans `project.source_dir`

**Étape 1 :** Renommer le fichier et la classe
**Étape 2 :** Ajouter `set_project(proj)` et `_update_header()`
**Étape 3 :** Ajuster les imports dans `main_window.py`
**Étape 4 :** `python -m compileall src` → OK
**Étape 5 :** Commit `refactor(gui): rename TranslateTab → PipelineTab, add project header`

---

### Task 3.2: Adapter PipelineTab pour utiliser le projet actif

**Objectif :** Le PipelineTab ne demande plus `source_lang`, `target_lang`, `output_format` — ces valeurs viennent du projet. Les fichiers à traduire sont ajoutés depuis n'importe où sur le disque (drop zone ou browse). Les résultats vont dans le dossier du projet.

**Simplification du layout Select :**
```
┌──────────────────────────────────────────────────────┐
│  🔵 Renegade Immortal — Pipeline                     │
│  EN → FR · Quality: Balanced · Output: TXT           │
│  Dossier: C:\Novels\Renegade\                        │
│──────────────────────────────────────────────────────│
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │     Drop files to translate here              │    │
│  │     (from anywhere on disk)                   │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
│  3 files queued                                       │
│              [▶ Start Translation]                    │
└──────────────────────────────────────────────────────┘
```

Les paramètres de langue/qualité/output sont hérités du projet. L'utilisateur peut les changer dans Project → Edit.

**Étape 1 :** Simplifier `_build_select_page` — retirer les combos langue/qualité/output
**Étape 2 :** `_on_start` utilise `self._project` pour ces valeurs
**Étape 3 :** Commit `feat(gui): pipeline tab inherits settings from active project`

---

## Phase 4 — GUI: FilesTab et GlossaryTab scopés

### Task 4.1: Reconstruire FilesTab en explorateur de fichiers du projet

**Objectif :** FilesTab devient un explorateur du dossier projet. Il liste tous les fichiers (source, en cours, terminés, erreurs) avec leur statut. Double-clic ouvre le fichier pour aperçu/vérification.

**Fichier :** `src/gui/tabs/files_tab.py` — réécriture conséquente.

**UI :**
```
┌──────────────────────────────────────────────────────────┐
│  📁 Fichiers — Renegade Immortal          [Filter: All ▼]│
│  Dossier: C:\Novels\Renegade\                            │
│──────────────────────────────────────────────────────────│
│  Fichier                  Statut      Taille    Actions  │
│  ─────────────────────────────────────────────────────── │
│  chapter_001_fr.txt       ✅ Done      42 KB    [👁 View]│
│  chapter_002_fr.txt       ✅ Done      38 KB    [👁 View]│
│  chapter_003_fr.txt       🔄 Working   15 KB    [⏸ Pause]│
│  chapter_004.txt          ❌ Error      8 KB    [🔄 Retry]│
│  chapter_005.txt          ⏳ Queued    12 KB    [✕ Remove]│
│  ─────────────────────────────────────────────────────── │
│  5 fichiers · 3 done, 1 working, 1 error, 1 queued       │
└──────────────────────────────────────────────────────────┘
```

**Actions par fichier :**
- 👁 **View** — ouvre le fichier (dans l'éditeur système ou une dialogue intégrée)
- 🔄 **Retry** — relance la trad pour ce fichier
- ⏸ **Pause/Resume** — contrôle par fichier
- ✕ **Remove** — retire de la file d'attente

**Étape 1 :** Réécrire `files_tab.py` :
  - `set_project(proj)` stocke le projet + son dossier
  - `refresh()` scanne le dossier projet pour lister les fichiers réels
  - Colonnes : Nom, Statut (avec icône), Taille, Actions
  - Double-clic → ouvre le fichier avec `os.startfile()` (éditeur par défaut)
  - Filtre par statut (All / Done / Working / Error / Queued)
**Étape 2 :** `python -m compileall src` → OK
**Étape 3 :** Commit `feat(gui): rebuild FilesTab as project file explorer`

---

### Task 4.2: Scoper GlossaryTab au projet actif

**Objectif :** GlossaryTab charge le lexique du projet actif. Le glossaire se construit automatiquement pendant la traduction.

**Fichier :** `src/gui/tabs/glossaries_tab.py`

**Changements :**
- Ajouter `set_project_id(pid)`
- `refresh()` appelle `/lexicon?project_id={pid}`
- Le label devient "Glossary of {project_name}"
- Note "Auto-built during translation" dans le header

**Étape 1 :** Ajouter `set_project_id()` + `_project_id` attr
**Étape 2 :** Modifier `refresh()` pour utiliser `project_id`
**Étape 3 :** Commit `feat(gui): scope GlossaryTab to active project`

---

### Task 4.3: Rafraîchissement automatique au changement de projet

**Objectif :** Quand le projet actif change (signal `projectActivated`), les 3 onglets dépendants se rafraîchissent automatiquement.

**Déjà fait dans Task 2.3.** Vérifier que :
- `_on_project_activated` appelle `self._pipeline_tab.set_project(proj)`
- `self._files_tab.set_project_id(pid)` + `self._files_tab.refresh()`
- `self._glossary_tab.set_project_id(pid)` + `self._glossary_tab.refresh()`

**Étape 1 :** Vérifier le câblage dans MainWindow
**Étape 2 :** Commit `fix(gui): auto-refresh dependent tabs on project switch`

---

## Phase 5 — Intégration et tests

### Task 5.1: Test de bout en bout

**Scénario :**
1. Lancer l'app
2. Onglet Projects → "+ New Project" → remplir → Create
3. Le projet apparaît dans la liste → cliquer "Open"
4. Onglet Pipeline → déposer un fichier .txt → Start
5. La traduction démarre → la progress bar avance
6. Onglet Files → les chunks apparaissent
7. Onglet Glossary → le glossaire se remplit automatiquement
8. Revenir sur Projects → créer un 2e projet → l'activer
9. Vérifier que Pipeline/Files/Glossary changent de contexte

**Étape 1 :** Test manuel complet
**Étape 2 :** Corriger les bugs découverts

---

### Task 5.2: Tests unitaires backend

```bash
python -m unittest discover tests -v
# Vérifier que 146+ tests passent toujours
```

---

### Task 5.3: Mise à jour CLI

**Fichier :** `src/backend/cli.py`

Ajouter les commandes :
```bash
python -m src.backend.cli project create --name "Renegade" --source-dir ...
python -m src.backend.cli project activate <id>
python -m src.backend.cli project delete <id>
python -m src.backend.cli project list
```

---

## Résumé des fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `src/gui/main_window.py` | SIDEBAR_ITEMS réordonné, connexion projectActivated, renommage attributs |
| `src/gui/tabs/projects_tab.py` | Réécriture complète — CRUD projets |
| `src/gui/tabs/pipeline_tab.py` | Renommé de translate_tab.py, header projet, simplification |
| `src/gui/tabs/files_tab.py` | `set_project_id()`, scope au projet |
| `src/gui/tabs/glossaries_tab.py` | `set_project_id()`, scope au projet |
| `src/gui/dialogs/project_dialog.py` | **NOUVEAU** — formulaire création/édition projet |
| `src/backend/routes/projects.py` | Routes PUT/DELETE/GET + activate |
| `src/backend/routes/schemas.py` | ProjectUpdateRequest schema |
| `src/backend/routes/chunks.py` | Paramètre `project_id` optionnel |
| `src/backend/routes/lexicon.py` | Paramètre `project_id` optionnel |
| `src/backend/orchestrator/state_store.py` | `set_active_project/get_active_project/clear_active_project` |
| `src/backend/cli.py` | Commandes `project create/activate/delete/list` |
| `tests/test_project_crud.py` | **NOUVEAU** — tests CRUD projet |

---

## Risques et points d'attention

1. **Régression du flux existant** — le TranslateTab actuel fait beaucoup de choses. Le renommer en PipelineTab ne doit rien casser. Je garde le `source_path` / `source_paths` existant dans le POST /projects.

2. **Projet actif vs projet en cours d'exécution** — le StateStore a déjà une notion de "projet courant" (celui qui tourne). Le "projet actif" pour le GUI est une notion distincte : c'est le projet sélectionné par l'utilisateur, qui peut ne pas être en cours d'exécution.

3. **Lexique par projet** — actuellement le `/lexicon` est global. Il faut soit le scoper par `project_id` dans la DB, soit utiliser le `project_id` comme filtre. La solution la plus simple : ajouter une colonne `project_id` à la table lexicon, avec fallback au comportement global si `project_id` est NULL.

4. **Migration des données existantes** — les projets créés avant cette refonte n'ont pas de `name` explicite. Il faut un fallback (utiliser le nom du dossier ou "Project-{id[:8]}").

5. **Pas de nouvel onglet** — le user a dit 5 onglets max. On remplace Translate par Pipeline, on garde Projects/Glossary/Files/Settings = 5 total. ✅

---

## Ordre d'implémentation recommandé

1. **Phase 1 (backend)** : CRUD projets → projet actif → scope routes
2. **Phase 2 (GUI Projects)** : SIDEBAR → ProjectsTab CRUD → câblage MainWindow
3. **Phase 3 (GUI Pipeline)** : Renommage → simplification
4. **Phase 4 (GUI Files/Glossary)** : Scope par projet
5. **Phase 5 (Intégration)** : Tests end-to-end → CLI → validation finale
