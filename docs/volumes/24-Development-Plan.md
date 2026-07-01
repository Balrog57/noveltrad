# Volume 24 — Plan de développement

## 24.1 Sprints

| Sprint | Durée | Objectif | Livrables | Definition of Done |
|--------|-------|----------|-----------|----------------------|
| 1 | 2 semaines | Fondation projet | Electron + Vue 3 + Vite + Pinia, routing, thème | `npm run dev` fonctionne, navigation entre 2 écrans |
| 2 | 2 semaines | Interface | Accueil, Projet, Paramètres, Console | Tous les écrans routés, tests de composants |
| 3 | 2 semaines | Gestion des projets | Création, ouverture, import source, SQLite | Projet créé via UI, fichier importé en chapitres |
| 4 | 1 semaine | SQLite + repositories | Schéma, migrations, CRUD, tests | 100 % des tables créées, repositories testés |
| 5 | 2 semaines | Ollama Manager | Providers, détection, pull, benchmark | Connexion Ollama testée, modèle téléchargé via UI |
| 6 | 2 semaines | Workflow Engine | Job/steps, worker, événements, retry | Workflow exécute 3 étapes de bout en bout |
| 7 | 2 semaines | Agents IA | 10 agents, prompts, validation | Chaque agent a 5 tests unitaires |
| 8 | 1 semaine | Lexique + TM | CRUD, fuzzy matching, import/export | Lexique appliqué, TM enrichie après traduction |
| 9 | 1 semaine | Cohérence + qualité | Métriques, scores, rapports | Rapport de cohérence généré, score QA < 70 bloque |
| 10 | 1 semaine | Export | Markdown, TXT, DOCX, EPUB | 4 formats exportables et valides |
| 11 | 1 semaine | Historique + Auto-update | Versions, diff, rollback, electron-updater | Diff affiché, mise à jour détectée |
| 12 | 2 semaines | Tests + release 1.0 | E2E, CI/CD, packaging, documentation | Tests E2E passent, release GitHub publiée |

---

## 24.2 Jalons

| Jalon | Date cible | Critère |
|-------|-----------|---------|
| MVP | Fin sprint 4 | Créer un projet, importer un chapitre, naviguer. |
| Alpha | Fin sprint 7 | Workflow complet sur un chapitre (10 agents). |
| Beta | Fin sprint 10 | Export + qualité + historique fonctionnels. |
| 1.0 | Fin sprint 12 | Auto-update + tests E2E + release publique. |

---

## 24.3 Dépendances entre sprints

```text
Sprint 1 (Foundation)
    ↓
Sprint 2 (UI) ←→ Sprint 3 (Projects) ←→ Sprint 4 (SQLite)
    ↓
Sprint 5 (Ollama) ←→ Sprint 6 (Workflow)
    ↓
Sprint 7 (Agents) ←→ Sprint 8 (Lexicon + TM)
    ↓
Sprint 9 (Consistency + Quality)
    ↓
Sprint 10 (Export) ←→ Sprint 11 (History + Auto-update)
    ↓
Sprint 12 (Tests + Release)
```

---

## 24.4 Ressources

### Équipe type

| Rôle | Profil | Implication |
|------|--------|-------------|
| Lead dev / architecte | Electron + Vue 3 + TypeScript | Temps plein |
| Développeur backend IA | Node.js, LLM, prompts | Temps plein |
| Développeur UI/UX | Vue 3, design system | Mi-temps |
| QA / testeur | Tests E2E, qualité | Mi-temps |

### Outils

- IDE : VS Code.
- Gestion de projet : GitHub Issues / Projects.
- Communication : Discord/Slack.
- CI/CD : GitHub Actions.

---

## 24.5 Risques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Ollama indisponible sur machine utilisateur | Haute | Bloquant | Wizard d’installation + fallback cloud. |
| Modèles locaux trop lents | Moyenne | Mauvaise UX | Modèles recommandés par ressources, benchmark. |
| Prompts peu fiables | Moyenne | Qualité faible | Fallback JSON, tests de prompts, calibration. |
| Difficultés packaging Electron | Moyenne | Retard release | Tests CI matrice OS dès le sprint 1. |
| Plugins malveillants | Faible | Élevé | Permissions, confirmation, marketplace revue. |

---

## 24.6 Definition of Done (DoD)

Pour qu’une fonctionnalité soit considérée terminée :

- [ ] Code écrit et typé.
- [ ] Tests unitaires passent.
- [ ] Tests d’intégration passent (si applicable).
- [ ] Documentation mise à jour.
- [ ] Revue de code effectuée.
- [ ] Pas de régression dans la CI.
- [ ] Accessible dans l’UI (si fonctionnalité visible).

---

## ✅ Critères d’acceptation globaux du plan

- [ ] Chaque sprint a des livrables mesurables.
- [ ] Les dépendances sont identifiées.
- [ ] Chaque jalon a un critère de passage.
- [ ] Les tests E2E couvrent les parcours critiques avant la 1.0.
- [ ] Les risques principaux ont une mitigation.
- [ ] La DoD est appliquée à chaque fonctionnalité.

---

## 📚 Références Context7

- Aucune référence externe spécifique.
