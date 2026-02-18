# Manuel Utilisateur - NovelTrad v1.6

## Introduction
NovelTrad est un outil de Traduction Assistée par Ordinateur (TAO) conçu pour les traducteurs de romans. Il combine des fonctionnalités classiques (Mémoire de Traduction, Glossaire) avec la puissance de l'IA pour offrir une expérience fluide.

## Installation
1. Téléchargez la dernière version depuis la section Releases.
2. Lancez l'installateur ou décompressez l'archive.
3. Exécutez `NovelTrad.exe`.

## Démarrage Rapide
1. **Créer un Projet** : 
   - Cliquez sur `Fichier > Nouveau Projet` (Ctrl+N).
   - Sélectionnez votre fichier source (.txt, .epub, .docx).
   - Choisissez les langues source et cible.
2. **Interface** :
   - **Gauche** : Liste des chapitres.
   - **Centre** : Éditeur de segments. Cliquez sur un segment pour l'activer.
   - **Droite** : Outils (Dictionnaire, Concordancier, IA).
3. **Traduire** :
   - Tapez votre traduction dans la zone de texte du segment actif.
   - Appuyez sur `Ctrl+Enter` pour valider et passer au suivant.
   - Utilisez `Ctrl+Space` pour insérer la meilleure suggestion.

## Fonctionnalités Avancées

### Mémoire de Traduction (TM / TMX)
- **Recherche** : Utilisez la barre de recherche "Concordancier" à droite pour trouver des termes dans votre projet ou votre mémoire.
- **Import/Export** :
  - `Fichier > Import TMX Memory...` : Chargez une mémoire existante (ex: d'un autre outil).
  - `Fichier > Export TMX Memory...` : Sauvegardez vos traductions validées pour les réutiliser ailleurs.

### Intelligence Artificielle (IA)
- **Traduction Automatique** : Cliquez sur l'icône "Baguette magique" dans un segment pour obtenir une pré-traduction (LLM ou NLLB).
- **Structure AI** : Détecte automatiquement les chapitres dans un gros fichier texte.
- **Glossary AI** : Analyse le texte pour extraire les noms propres et termes récurrents.

### Outils de Qualité
- **Vérification (QA)** : `Outils > Run QA Check` détecte les oublis (nombres, ponctuation, balises).
- **Alignement** : `Outils > Alignment Tool` permet de créer une mémoire à partir d'un original et sa traduction existante.

## Raccourcis Clavier
- `Ctrl+S` : Sauvegarder le segment courant.
- `Ctrl+F` : Rechercher / Remplacer.
- `Ctrl+,` : Paramètres.
- `F1` : Aide (ce manuel).
