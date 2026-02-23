# Planification et Suivi - Refactorisation MainWindow

## Objectifs de la Session
- [x] Phase 0 : Audit de l'architecture GUI actuelle et Modularisation Initiale
- [x] Phase 1 : Migration de la gestion des chapitres et segments (`EditorController`)
- [x] Phase 2 : Migration de la logique Outils (`ToolsController`)
- [x] Phase 3 : Validation et Audit Final (Tests pytest)
- [x] Phase 4 : Vérification du Lancement (Smoke Test et corrections UI)

## Implémentation
- [x] Étape 1 : Création de `src/gui/controllers/` et `src/gui/panels/`
- [x] Étape 2 : Injection de la nouvelle structure dans `MainWindow`
- [x] Étape 3 : Routage des menus et raccourcis
- [x] Étape 4 : Suppression chirurgicale du code mort (~1300 lignes retirées)
- [x] Étape 5 : Validation du lancement avec installation de `PyQt6-WebEngine`

## Révision
- [x] Code modulaire (Panels + Controllers)
- [x] MainWindow réduit de 2149 lignes à ~740 lignes
- [x] Menus fonctionnels via contrôleurs
- [x] Smoke test réussi : Application stable et modulaire
- [x] Dépendances corrigées (`PyQt6-WebEngine`)
