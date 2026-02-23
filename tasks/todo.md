# Planification et Suivi - Refactorisation MainWindow

## Objectifs de la Session
- [x] Audit de l'architecture GUI actuelle
- [x] Modularisation de `MainWindow.py` (Phase 0)
    - [x] Extraction des contrôleurs (`Project`, `AI`, `TM`)
    - [x] Création des panneaux (`Header`, `Footer`, `Tools`)
    - [x] Routage complet des menus
    - [x] Nettoyage massif de `MainWindow.py` (Gain de 50% en lisibilité)
- [ ] Phase 1 : Migration de la gestion des chapitres et segments

## Implémentation
- Étape 1 : Création de `src/gui/controllers/`
- Étape 2 : Création de `src/gui/panels/`
- Étape 3 : Injection de la nouvelle structure dans `MainWindow.init_ui()` et `MainWindow.setup_workspace()`
- Étape 4 : Routage des menus vers les contrôleurs
- Étape 5 : Suppression chirurgicale du code mort

## Révision
- [x] Code modulaire (Panels + Controllers)
- [x] MainWindow réduit de 2149 lignes à ~1000 lignes
- [x] Menus fonctionnels via contrôleurs
- [x] Absence de code legacy `setup_workspace_legacy`
