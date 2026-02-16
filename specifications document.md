# cahier_des_charges_noveltrad_v2.docx

CAHIER DES CHARGES

NovelTrad

Application de Traduction Assistée par Ordinateur

pour Romans et Web Novels

Xianxia • Science-Fiction • Fantasy • Romance • Tous genres

Version 2.0

Février 2026

# 0. Règles de Développement et Références Standards

> [!IMPORTANT]
> **Règle d'Or du Workspace**
> Tout développement, ajout de fonctionnalité ou modification doit se référer strictement aux sources suivantes :
> 1. **Ce présent document** (`specifications document.md`) pour le périmètre fonctionnel.
> 2. **Définition standard TAO** (Source : [Wikipedia](https://fr.wikipedia.org/wiki/Traduction_assist%C3%A9e_par_ordinateur)) : Le logiciel doit inclure les fonctions piliers (Mémoire de Traduction, Gestionnaire de Terminologie, Concordancier, Alignement).
> 3. **Standards IA & UX** (Source : [AI Novel Translation](https://www.ainoveltranslation.com/)) : L'interface et les fonctions IA doivent viser le niveau de fluidité et de puissance de cet outil de référence (Glossary AI, Batch Translation, Structure AI).

# Table des matières

1. Présentation générale du projet

2. Objectifs et périmètre

3. Architecture technique

4. Interface utilisateur

5. Moteurs de traduction

6. Gestion des formats de fichiers et préservation du formatage

7. Glossaire AI (génération automatique par IA)

8. Gestion des glossaires manuels

9. Dictionnaire local

10. Intégration IA (locale et en ligne)

11. Gestion des projets

12. Fonctionnalités détaillées

13. Exigences non fonctionnelles

14. Stack technique recommandée

15. Modèle de données

16. Phases de développement

17. Annexes

# 1. Présentation générale du projet

Le projet NovelTrad est une application de bureau développée en Python, conçue pour assister la traduction de romans et de livres numériques de toute nature : web novels chinois (xianxia, wuxia, xuanhuan), science-fiction, fantasy, romance, littérature générale, ou tout autre genre. L’application combine les fonctionnalités d’un outil de TAO (Traduction Assistée par Ordinateur) inspiré d’OmegaT, la puissance de la traduction automatique neuronale locale (NLLB via ctranslate2, MarianMT via Argos Translate), et l’intégration d’IA génératives locales ou en ligne.

Cas d’usage principal : traduire des romans déjà traduits en anglais (depuis le chinois, le japonais, le coréen, etc.) vers le français, mais également traduire directement depuis n’importe quelle langue source vers n’importe quelle langue cible supportée par les modèles.

## 1.1 Inspirations

- OmegaT : gestion de projets de traduction, mémoires de traduction, glossaires, vue segmentée
- AI Novel Translation : traduction automatisée de romans par chapitres, Glossary AI automatique, préservation du formatage EPUB/DOCX, Editor AI, Structure AI, instructions personnalisées
- Bookfere Translator : interface bilingue côte à côte, traduction par paragraphes
## 1.2 Public cible

- Traducteurs amateurs et passionnés de web novels et de littérature étrangère
- Lecteurs souhaitant accéder à des romans non disponibles dans leur langue
- Traducteurs semi-professionnels cherchant un outil gratuit, hors ligne et personnalisable
## 1.3 Genres et contenus supportés

L’application n’est pas limitée à un genre. Elle prend en charge tout type de roman ou document textuel :

- Web novels : xianxia, wuxia, xuanhuan, cultivation, light novels japonais, web novels coréens
- Littérature de genre : science-fiction, fantasy, thriller, romance, horreur, policier
- Littérature générale : classiques, fiction contemporaine, essais
- Documents divers : manuels, guides, textes académiques (dans la mesure du raisonnable)
# 2. Objectifs et périmètre

## 2.1 Objectifs principaux

- Fournir une interface bilingue avec affichage côte à côte ou dessus/dessous des paragraphes originaux et traduits
- Permettre la traduction automatique locale sans connexion internet via NLLB et Argos Translate
- Supporter les formats TXT, EPUB, PDF et DOCX en entrée, avec préservation du formatage original pour EPUB et DOCX
- Gérer un système de Glossary AI capable de générer automatiquement un glossaire à partir du texte source via IA
- Gérer des glossaires manuels complémentaires avec catégories spécifiques par genre (xianxia, SF, etc.)
- Intégrer un dictionnaire local multilingue
- Permettre l’utilisation d’IA génératives locales (LM Studio, Ollama) ou en ligne pour améliorer/raffiner les traductions
- Offrir en option la traduction via services web gratuits (Google Translate sans API) pour des segments individuels
- Synchroniser la navigation entre texte source et texte cible (clic sur un paragraphe = navigation automatique vers le paragraphe correspondant)
## 2.2 Hors périmètre (v1)

- Application web ou mobile (application desktop uniquement)
- Traduction collaborative multi-utilisateurs en temps réel
- OCR intégré pour images de texte (possible en v2)
- Publication directe sur plateformes de lecture
# 3. Architecture technique

## 3.1 Vue d’ensemble

L’application suit une architecture modulaire en couches, permettant l’ajout facile de nouveaux moteurs de traduction, de nouveaux formats de fichiers ou de nouvelles fonctionnalités.

## 3.2 Diagramme d’architecture simplifié

[Interface PyQt6]

│

└─── [Contrôleur de projet]

│

┌───────┼─────────┬───────────┐

│              │            │              │

[Format      [Moteurs de   [Glossary    [SQLite

Handlers]    Traduction]    AI]          DB]

│              │

[EPUB/DOCX/  [NLLB|Argos|

PDF/TXT]     Web|IA LLM]

# 4. Interface utilisateur

## 4.1 Fenêtre principale

La fenêtre principale se compose de plusieurs zones distinctes, redimensionnables par l’utilisateur.

Barre de menu

- Fichier : Nouveau projet, Ouvrir, Sauvegarder, Importer (TXT/EPUB/PDF/DOCX), Exporter, Quitter
- Édition : Annuler, Rétablir, Rechercher/Remplacer
- Traduction : Traduire le paragraphe, Traduire la sélection, Traduire tout le chapitre, Traduire en lot (batch), Choisir le moteur
- Glossaire : Ouvrir le glossaire, Ajouter une entrée, Générer Glossary AI, Importer/Exporter
- Dictionnaire : Rechercher un mot, Configurer les dictionnaires
- IA : Configurer les modèles, Raffiner la traduction, Editor AI, Poser une question contextuelle
- Outils : Paramètres, Télécharger des modèles, Statistiques du projet, Instructions personnalisées
- Aide : Documentation, À propos
Zone d’édition bilingue

La zone centrale est divisée en deux panneaux synchronisés :

- Panneau source (gauche ou haut) : affiche le texte original, non éditable par défaut
- Panneau cible (droite ou bas) : affiche la traduction, entièrement éditable
- Basculement entre affichage côte à côte (horizontal) et dessus/dessous (vertical) via un bouton ou raccourci
- Synchronisation du défilement : le clic ou le positionnement du curseur sur un paragraphe dans un panneau met en surbrillance et fait défiler automatiquement vers le paragraphe correspondant dans l’autre panneau
- Numérotation des paragraphes visible dans les deux panneaux
- Code couleur : paragraphes non traduits (rouge/gris), traduits automatiquement (orange), traduits et validés manuellement (vert), raffinés par IA (bleu)
Panneau inférieur

- Onglet Glossaire : termes du glossaire détectés dans le paragraphe courant, avec option d’ajout rapide
- Onglet Dictionnaire : résultats de recherche du dictionnaire local
- Onglet Mémoire de traduction : segments similaires déjà traduits
- Onglet IA : interface de chat contextuel avec le modèle IA configuré
- Onglet Commentaires/Notes : notes du traducteur par paragraphe
## 4.2 Modes d’affichage

# 5. Moteurs de traduction

L’application propose une couche d’abstraction unifiée (TranslationEngine) permettant d’utiliser différents moteurs de traduction de manière interchangeable.

## 5.1 NLLB via ctranslate2 (moteur principal)

- Modèle : Meta NLLB-200 (600M, 1.3B, ou 3.3B selon les ressources matérielles)
- Bibliothèque : ctranslate2 pour l’inférence optimisée (CPU et GPU)
- Langues : support de 200+ langues, focus principal sur eng_Latn → fra_Latn, mais également zho_Hans, jpn_Jpan, kor_Hang, etc.
- Avantages : excellent support multilingue, traduction hors ligne, performant même sur CPU
- Configuration : choix de la taille du modèle, device (CPU/GPU), précision (int8, float16)
- Téléchargement : gestionnaire intégré pour télécharger et gérer les modèles locaux
## 5.2 Argos Translate (MarianMT)

- Bibliothèque : argostranslate, utilisant des modèles MarianMT
- Langues : packages de langues téléchargeables (en → fr, zh → en, ja → en, ko → en, etc.)
- Mode pivot : possibilité de traduction en deux étapes (ex: ja → en → fr) si pas de package direct
- Avantages : léger, rapide, totalement hors ligne
- Gestion intégrée de l’installation des packages de langues
## 5.3 Traduction par IA (LLM)

Utilisation d’un LLM (local ou en ligne) comme moteur de traduction principal, particulièrement pertinent pour les romans car les LLM comprennent mieux le contexte narratif.

- Le texte source est envoyé au LLM avec un prompt de traduction spécifique au genre
- Le glossaire du projet est injecté dans le prompt pour garantir la cohérence
- Le contexte des paragraphes précédents peut être inclus pour maintenir la cohérence narrative
- Instructions personnalisées par l’utilisateur (ton, style, registre de langue)
## 5.4 Services web gratuits (complémentaire)

- Google Translate (sans API) : via bibliothèque deep-translator ou googletrans
- Utilisation limitée : traduction de segments individuels ou paragraphes courts uniquement
- Avertissement explicite à l’utilisateur sur les limitations (rate limiting, instabilité)
- Non recommandé pour la traduction de chapitres entiers (préférer la traduction locale)
- Autres services envisageables : LibreTranslate (auto-hébergé), DeepL gratuit (limité)
## 5.5 Interface unifiée des moteurs

class TranslationEngine(ABC):

def translate(text, src_lang, tgt_lang, glossary=None, context=None) -> str

def translate_batch(texts, src_lang, tgt_lang, glossary=None) -> list[str]

def get_supported_languages() -> list[tuple]

def get_name() -> str

def is_available() -> bool

def supports_context() -> bool  # True pour LLM, False pour NMT

# 6. Gestion des formats de fichiers et préservation du formatage

Un point central de l’application est la capacité à travailler avec différents formats de fichiers tout en préservant le formatage original lors de la traduction, particulièrement pour les formats EPUB et DOCX.

## 6.1 Formats supportés en détail

## 6.2 Préservation du formatage EPUB

Lors de l’import d’un fichier EPUB, le système :

- Extrait le contenu XHTML de chaque chapitre/section via ebooklib
- Parse le HTML et identifie les noeuds textuels à traduire (en ignorant les balises de structure, images, CSS)
- Stocke chaque segment textuel avec sa position dans l’arbre DOM
- Après traduction, réinsère le texte traduit aux mêmes positions dans le DOM
- Reconstruit l’EPUB avec tous les assets originaux (images, CSS, polices, métadonnées, NCX/NAV)
Résultat : un EPUB traduit visuellement identique à l’original, seul le texte change.

## 6.3 Préservation du formatage DOCX

Lors de l’import d’un fichier DOCX, le système :

- Décompresse et parse le XML interne (via python-docx)
- Identifie les runs de texte dans chaque paragraphe tout en préservant les propriétés de formatage (gras, italique, police, taille, couleur, etc.)
- Traduit le contenu textuel de chaque run
- Réinsère le texte traduit dans les mêmes runs XML avec leurs propriétés de style intactes
- Les images, en-têtes, pieds de page, tableaux, listes et styles restent inchangés
Résultat : un DOCX traduit conservant exactement le même formatage que l’original.

## 6.4 Gestion du PDF

Le PDF étant un format orienté mise en page (et non orienté texte), la préservation parfaite est techniquement difficile. L’approche retenue :

- Import : extraction du texte via PyMuPDF (fitz) ou pdfplumber, avec détection de la structure (titres, paragraphes, notes)
- Travail interne : le texte extrait est traité comme du TXT structuré
- Export : génération d’un nouveau PDF via ReportLab ou WeasyPrint avec une mise en page soignée (mais pas identique à l’original)
- Option : export en EPUB ou DOCX à partir d’un import PDF pour une meilleure flexibilité
# 7. Glossary AI (génération automatique par IA)

Inspiré de la fonctionnalité Glossary AI d’AI Novel Translation, ce module utilise l’IA (locale ou en ligne) pour analyser automatiquement le texte source et générer un glossaire complet des termes importants.

## 7.1 Principe de fonctionnement

- L’utilisateur déclenche la génération du glossaire via le menu ou lors de la création d’un projet
- Le système envoie le texte source (ou un échantillon représentatif) au LLM configuré
- Le LLM identifie et extrait les termes importants : noms de personnages, lieux, concepts récurrents, termes spécifiques au genre, titres, organisations
- Pour chaque terme, le LLM propose une traduction cohérente et une catégorisation
- Le glossaire généré est présenté à l’utilisateur pour validation, modification ou complétion
- Le glossaire validé est automatiquement appliqué lors des traductions suivantes
## 7.2 Prompts Glossary AI par genre

Des prompts spécifiques sont préconfigurés selon le genre détecté ou choisi :

## 7.3 Glossary AI incrémental

Le Glossary AI ne se limite pas à une analyse initiale. Il s’enrichit au fil de la traduction :

- À chaque nouveau chapitre, les nouveaux termes détectés sont proposés en complément du glossaire existant
- Les termes existants sont renforcés par de nouveaux contextes d’utilisation
- L’utilisateur peut activer/désactiver la génération automatique à chaque chapitre
- Les termes générés par l’IA sont marqués comme « auto-générés » et ceux validés par l’utilisateur comme « validés »
## 7.4 Application du glossaire à la traduction

Le glossaire (qu’il soit généré par IA ou manuel) est utilisé de deux manières complémentaires :

- Injection dans le prompt : pour les traductions par LLM, le glossaire pertinent est injecté dans le contexte du prompt afin que le modèle les utilise directement
- Post-traitement : pour les moteurs NMT (NLLB, Argos), le glossaire est appliqué en remplacement après la traduction, par ordre de priorité
# 8. Gestion des glossaires manuels

## 8.1 Structure d’une entrée de glossaire

## 8.2 Fonctionnalités

- Détection automatique des termes du glossaire dans le texte source avec mise en surbrillance
- Ajout rapide depuis l’interface (sélection dans le texte → clic droit → ajouter au glossaire)
- Import/Export aux formats CSV, TSV, TBX (compatibilité OmegaT)
- Glossaires hiérarchiques : glossaire global + glossaire par projet
- Recherche, filtrage et tri dans le glossaire
- Fusion de glossaires entre projets
- Historique des modifications
# 9. Dictionnaire local

## 9.1 Sources de données

- CC-CEDICT : dictionnaire chinois-anglais libre de droits
- CFDICT : dictionnaire chinois-français communautaire
- JMdict/EDICT : dictionnaire japonais-anglais
- Wiktionary dumps : couverture multilingue large
- Possibilité d’importer des dictionnaires au format StarDict, XDXF, ou CSV
## 9.2 Fonctionnalités

- Recherche instantanée par mot source, transcription phonétique ou traduction
- Affichage automatique de la définition au survol d’un mot dans le texte source (tooltip)
- Historique des recherches
- Possibilité d’ajouter des définitions personnalisées
- Segmentation automatique du chinois (via jieba ou pkuseg) pour les textes chinois
## 9.3 Stockage

Le dictionnaire est stocké dans une base SQLite locale, indexée pour des recherches rapides. La base est préchargée au démarrage en mémoire pour des performances optimales.

# 10. Intégration IA (locale et en ligne)

## 10.1 IA locale via LM Studio / Ollama

- Connexion via API REST locale compatible OpenAI (ex: http://localhost:1234/v1 pour LM Studio, http://localhost:11434/v1 pour Ollama)
- Support du format OpenAI Chat Completions (messages, temperature, max_tokens)
- Configuration de l’URL, du modèle, et des paramètres d’inférence
- Détection automatique des modèles disponibles via l’endpoint /v1/models
- Modèles recommandés : Qwen2.5, Yi, DeepSeek, Mistral, Llama, ou tout modèle multilingue
## 10.2 IA en ligne

- Support des API compatibles OpenAI (OpenAI, Anthropic via adaptateur, Mistral, Groq, Together, etc.)
- Configuration de la clé API, du endpoint, et du modèle
- Gestion du coût : estimation du nombre de tokens et du coût avant traduction
## 10.3 Cas d’utilisation de l’IA

- Traduction directe : utiliser le LLM comme moteur de traduction principal (meilleure qualité pour les romans)
- Raffinage (Editor AI) : envoyer la traduction machine à l’IA pour améliorer la fluidité et la cohérence
- Glossary AI : génération automatique du glossaire (voir section 7)
- Explication de termes : demander à l’IA d’expliquer un terme ou passage difficile
- Suggestions multiples : obtenir plusieurs propositions de traduction pour un segment
- Chat contextuel : poser des questions libres sur le texte en cours de traduction
## 10.4 Instructions personnalisées (Custom Instructions)

Inspiré d’AI Novel Translation, l’utilisateur peut définir des instructions personnalisées qui seront injectées dans tous les prompts IA du projet :

- Ton et style de traduction souhaité (littéraire, familier, neutre, etc.)
- Conventions de nommage (garder certains termes en langue originale, etc.)
- Registre de langue (tutoiement/vouvoiement, règles de genre, etc.)
- Instructions spécifiques au roman (contexte général de l’histoire, époque, univers)
- Sauvegarde par projet et possibilité de réutiliser entre projets
## 10.5 Prompts préconfigurés

- Prompt de traduction général : contexte du genre, instructions sur le style, glossaire injecté
- Prompt de traduction xianxia : spécificités du genre (cultivation, honorifiques, etc.)
- Prompt de raffinage (Editor AI) : améliorer la fluidité tout en restant fidèle au sens
- Prompt d’explication : expliquer les références culturelles et termes spécifiques
- Prompt personnalisable : l’utilisateur peut créer et sauvegarder ses propres modèles de prompts
# 11. Gestion des projets

## 11.1 Structure d’un projet

projet_roman/

├── project.json            # Métadonnées (genre, langues, instructions custom)

├── source/                 # Fichiers originaux

│   ├── original.epub       # ou .docx, .pdf, .txt

│   ├── chapitre_001.txt    # Texte extrait (si EPUB/DOCX/PDF)

│   └── chapitre_002.txt

├── target/                 # Fichiers traduits

│   ├── translated.epub     # EPUB traduit avec formatage préservé

│   ├── chapitre_001.txt

│   └── chapitre_002.txt

├── glossary/               # Glossaires (manuel + AI)

├── tm/                     # Mémoire de traduction

├── prompts/                # Prompts personnalisés

└── notes/                  # Notes du traducteur

## 11.2 Métadonnées du projet

- Nom du roman / titre du projet
- Langue source et langue cible
- Genre (xianxia, SF, fantasy, romance, général, personnalisé)
- Moteur de traduction par défaut
- Instructions personnalisées
- Format source original (pour la préservation du formatage)
- Statistiques (progression, dernière modification, etc.)
## 11.3 Synchronisation source/cible

Le système maintient un alignement paragraphe par paragraphe entre le texte source et le texte cible. Chaque paragraphe est identifié par un index unique. Lorsque le curseur se positionne sur un paragraphe dans l’un des panneaux, l’autre panneau défile automatiquement vers le paragraphe correspondant avec mise en surbrillance.

# 12. Fonctionnalités détaillées

## 12.1 Traduction par lot (batch)

- Traduction automatique d’un chapitre entier ou de tout le livre en un clic
- Barre de progression avec estimation du temps restant
- Possibilité de mettre en pause et reprendre
- Application automatique du glossaire en post-traitement
- File d’attente de chapitres à traduire
- Option de préservation du formatage pour EPUB et DOCX
## 12.2 Editor AI (raffinage par IA)

Inspiré de la fonctionnalité Editor AI d’AI Novel Translation :

- Après une traduction machine (NLLB, Argos), l’IA relit et corrige la traduction
- Améliore la fluidité, la grammaire, la cohérence stylistique
- Tient compte du glossaire pour maintenir la cohérence terminologique
- Applicable paragraphe par paragraphe ou en lot
## 12.3 Structure AI (détection automatique des chapitres)

- Pour les fichiers TXT longs ou les EPUB mal structurés, l’IA détecte automatiquement les séparations de chapitres
- Propose un découpage que l’utilisateur peut valider ou ajuster
- Nommage automatique des chapitres par l’IA
## 12.4 Mémoire de traduction (TM)

- Stockage automatique des paires source/cible validées
- Recherche de correspondances floues (fuzzy matching) pour les nouveaux segments
- Affichage des correspondances avec pourcentage de similarité
- Import/export au format TMX
- Mémoire globale et mémoire par projet
## 12.5 Rechercher et remplacer

- Recherche dans le texte source et/ou cible
- Remplacement simple ou avec expressions régulières
- Recherche dans tous les chapitres du projet
- Remplacement en lot dans le glossaire
## 12.6 Statistiques du projet

- Nombre de caractères/mots source et cible
- Progression de la traduction (paragraphes traduits vs. total)
- Répartition par statut (non traduit, machine, raffiné, validé)
- Vitesse de traduction moyenne
- Coût estimé si utilisation d’IA en ligne
## 12.7 Raccourcis clavier

## 12.8 Concordancier (Fonctionnalité TAO Standard)
- Recherche de termes dans le contexte des traductions précédentes (TM) et des corpus de référence.
- Affichage des segments source/cible contenant le terme recherché pour vérifier l'usage en contexte.

## 12.9 Assurance Qualité (QA Check)
- Vérification automatique avant export :
    - Balises manquantes ou altérées.
    - Incohérence des nombres/chiffres.
    - Termes du glossaire non respectés (si forcé).
    - Segments vides ou non traduits.
    - Ponctuation finale différente de la source.

# 13. Exigences non fonctionnelles

## 13.1 Performance

- Traduction d’un paragraphe (NLLB) : < 3 secondes sur CPU moderne
- Traduction d’un chapitre (~5000 mots) : < 90 secondes via NMT, variable via LLM
- Génération Glossary AI pour un chapitre : < 30 secondes via LLM local
- Démarrage de l’application : < 5 secondes (hors chargement du modèle)
- Chargement d’un modèle NLLB : < 30 secondes
- Ouverture d’un EPUB de 500 pages : < 10 secondes
- Export EPUB/DOCX avec préservation du formatage : < 30 secondes
- Recherche dans le dictionnaire : < 100ms
## 13.2 Compatibilité

- Systèmes d’exploitation : Windows 10/11, macOS 12+, Linux (Ubuntu 22.04+)
- Python 3.10 ou supérieur
- Support GPU optionnel (CUDA pour NVIDIA, accélération Metal pour macOS)
- Fonctionnement complet hors ligne (sauf services web et IA en ligne)
## 13.3 Utilisabilité

- Interface entièrement en français (internationalisation possible en v2)
- Thème clair et sombre
- Polices configurables pour toutes les langues
- Sauvegarde automatique régulière (configurable)
- Annulation multi-niveaux (Ctrl+Z)
- Assistant de premier lancement pour configurer les modèles et télécharger les dictionnaires
## 13.4 Sécurité et données

- Toutes les données restent en local (aucun envoi à des serveurs tiers sauf activation explicite d’un service en ligne)
- Clés API stockées de manière sécurisée (keyring ou chiffrement local)
- Pas de télémétrie ni de collecte de données
# 14. Stack technique recommandée

# 15. Modèle de données

Schéma principal de la base SQLite :

## 15.1 Table projects

id INTEGER PRIMARY KEY

name TEXT NOT NULL

source_lang TEXT NOT NULL

target_lang TEXT NOT NULL

genre TEXT  -- 'xianxia', 'scifi', 'fantasy', 'romance', 'general', 'custom'

source_format TEXT  -- 'txt', 'epub', 'docx', 'pdf'

custom_instructions TEXT

default_engine TEXT

created_at DATETIME

updated_at DATETIME

## 15.2 Table chapters

id INTEGER PRIMARY KEY

project_id INTEGER FK -> projects

title TEXT

source_path TEXT

target_path TEXT

status TEXT  -- 'pending', 'in_progress', 'translated', 'reviewed'

order_index INTEGER

## 15.3 Table segments

id INTEGER PRIMARY KEY

chapter_id INTEGER FK -> chapters

paragraph_index INTEGER

source_text TEXT

target_text TEXT

status TEXT  -- 'untranslated', 'machine', 'ai_refined', 'validated'

engine_used TEXT

last_modified DATETIME

## 15.4 Table glossary

id INTEGER PRIMARY KEY

project_id INTEGER  -- NULL = global

source_term TEXT NOT NULL

target_term TEXT NOT NULL

variants TEXT  -- JSON array of alternate spellings

category TEXT

context TEXT

priority INTEGER DEFAULT 0

source TEXT  -- 'manual', 'ai_generated', 'validated'

created_at DATETIME

## 15.5 Table dictionary

id INTEGER PRIMARY KEY

word TEXT NOT NULL

reading TEXT  -- pinyin, romaji, etc.

lang TEXT  -- 'zh', 'ja', 'ko', etc.

definitions TEXT  -- JSON {"en": "...", "fr": "..."}

## 15.6 Table translation_memory

id INTEGER PRIMARY KEY

source_text TEXT

target_text TEXT

source_lang TEXT

target_lang TEXT

project_id INTEGER

created_at DATETIME

# 16. Phases de développement

## Phase 1 – Fondations (4-6 semaines)

- Mise en place du projet Python et de l’architecture modulaire
- Interface de base PyQt6 avec double panneau synchronisé (navigation croisée par paragraphe)
- Gestion de projets (création, ouverture, sauvegarde)
- Chargement de fichiers TXT
- Intégration du premier moteur : NLLB via ctranslate2
- Traduction paragraphe par paragraphe et par lot
## Phase 2 – Formats et glossaires (4-6 semaines)

- Support EPUB avec préservation complète du formatage
- Support DOCX avec préservation complète du formatage
- Support PDF (import texte + export reconstruit)
- Intégration d’Argos Translate
- Système de glossaires manuels complet (CRUD, import/export)
- Dictionnaire local avec CC-CEDICT et JMdict
- Mémoire de traduction basique
## Phase 3 – IA et Glossary AI (4-5 semaines)

- Intégration IA locale (LM Studio / Ollama) comme moteur de traduction
- Intégration IA en ligne (API OpenAI-compatible)
- Glossary AI : génération automatique de glossaire par IA avec prompts par genre
- Editor AI : raffinage des traductions machine par IA
- Structure AI : détection automatique des chapitres
- Chat contextuel IA
- Instructions personnalisées (Custom Instructions)
- Services web complémentaires (Google Translate)
## Phase 4 – Finalisation (3-4 semaines)

- Thème sombre
- Statistiques du projet et estimation de coûts
- Assistant de premier lancement
- Packaging en exécutable (PyInstaller)
- Tests complets, corrections de bugs
- Documentation utilisateur
# 17. Annexes

## 17.1 Exemple de glossaire xianxia par défaut

## 17.2 Exemple de prompt Glossary AI (genre SF)

Voici un exemple de prompt utilisé par le module Glossary AI pour un roman de science-fiction :

"Analyse le texte suivant, extrait d’un roman de science-fiction.

Identifie et liste tous les termes importants qui nécessitent

une traduction cohérente tout au long du roman :

- Noms de personnages (et surnoms/titres associés)

- Noms de vaisseaux, stations, planètes, systèmes stellaires

- Technologies fictives, armes, équipements

- Races, espèces, factions, organisations

- Rangs militaires ou hiérarchiques spécifiques

- Termes scientifiques propres à l’univers du roman

Pour chaque terme, fournis : terme_source, traduction_proposée,

catégorie, et une courte note de contexte.

Réponds en JSON."

## 17.3 Ressources et références

- NLLB-200 : https://github.com/facebookresearch/fairseq/tree/nllb
- ctranslate2 : https://github.com/OpenNMT/CTranslate2
- Argos Translate : https://github.com/argosopentech/argos-translate
- CC-CEDICT : https://www.mdbg.net/chinese/dictionary?page=cedict
- JMdict : https://www.edrdg.org/jmdict/j_jmdict.html
- OmegaT : https://omegat.org
- AI Novel Translation : https://www.ainoveltranslation.com
- LM Studio : https://lmstudio.ai
- Ollama : https://ollama.com
- PyQt6 : https://www.riverbankcomputing.com/software/pyqt/
- ebooklib : https://github.com/aerkalov/ebooklib
- python-docx : https://python-docx.readthedocs.io
- PyMuPDF : https://pymupdf.readthedocs.io
