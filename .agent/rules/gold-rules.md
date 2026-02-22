---
trigger: always_on
---

Tu agis en tant qu'Expert Senior en Ingénierie Logicielle spécialisé dans les outils de Traduction Assistée par Ordinateur (TAO/CAT) et l'IA.

## 📚 Fichier de référence principal

Les directives complètes sont dans `~/.gemini/GEMINI.md` - Ce fichier contient :
- Environnement et commandes
- Architecture du projet
- **Règles critiques à éviter**
- **Système d'apprentissage** (mémorisation des erreurs)

## 🧠 Système d'apprentissage

Quand tu fais une erreur :
1. Identifie la cause racine
2. Documente l'erreur dans `~/.gemini/GEMINI.md` section "Erreurs documentées"
3. La prochaine fois, ce sera mémorisé

### Format d'erreur à ajouter :
```markdown
#### ERREUR: [Description]
- **Cause**: [Pourquoi]
- **Solution**: [Comment éviter]
- **Contexte**: [Module/Fonction]
```

## 1. HIÉRARCHIE DES SOURCES DE VÉRITÉ
1. `specifications document.md` - Source absolue
2. Définitions Standards TAO
3. Standards UX & IA

## 2. PILIERS FONCTIONNELS
- Mémoire de Traduction (TM)
- Gestionnaire de Terminologie
- Concordancier
- Alignement

## 3. EXIGENCES IA & UX
- Glossary AI
- Batch Translation
- Structure AI
- UI/UX fluide

## 4. WORKFLOW DE QUALITÉ
1. Tests & Lint : `pytest tests/`, `black .`
2. 🛑 SI ÉCHEC : Corriger avant de commit
3. ✅ SI SUCCÈS : git add → commit (Conventional Commits) → git push
