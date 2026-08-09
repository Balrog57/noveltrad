# NovelTrad — SDD

**Licence du projet et de l'implémentation : GNU Affero General Public License v3.0 uniquement (`AGPL-3.0-only`).**

NovelTrad est un fork de [TranslateBooksWithLLMs](https://github.com/hydropix/TranslateBooksWithLLMs) (AGPL-3.0). Le présent document décrit la version NovelTrad de ce fork : périmètre, évolutions apportées, éléments conservés et éléments supprimés. En cas de divergence entre ce SDD et le code, le code est un défaut à corriger ; ce document reste la référence normative unique.

# Chapitre 1 — Vision, objectifs et périmètre

## 1.1 Vision

NovelTrad est une application locale de traduction de livres et de documents assistée par intelligence artificielle. Dépôt d'un fichier, choix d'une langue, obtention du résultat : le fork TBL fournit environ 99 % de ce périmètre. NovelTrad ajoute un jeu de fournisseurs IA étendu et un pipeline multipasse optionnel déclenché par l'option « Raffiner ». Il retire toute marque d'attribution « Traduit avec TranslateBook via LLM (TBL) » des fichiers produits.

## 1.2 Origine et statut du projet

NovelTrad reprend le dépôt `hydropix/TranslateBooksWithLLMs` sous la forme d'un fork persistant nommé `noveltrad`. Toutes les fonctionnalités de TBL non explicitement supprimées ou modifiées par ce SDD sont conservées telles quelles, avec leurs tests. Le dépôt de référence, les obligations AGPL-3.0 et les notices de copyright des fichiers repris restent applicables (voir chapitre 18).

## 1.3 Objectifs

- Simplicité : déposer un fichier, choisir une langue, obtenir le résultat.
- Qualité : viser une traduction nécessitant le moins d'intervention humaine possible ; la multipasse « Raffiner » améliore la cohérence, l'orthographe, la grammaire et le style.
- Robustesse : reprise après interruption sans perte (checkpoints).
- Local-first : les fournisseurs locaux (Ollama, serveurs OpenAI-compatibles) fonctionnent hors ligne ; les fournisseurs cloud exigent une clé API.
- Préservation : les formats d'entrée (EPUB, SRT, DOCX, TXT) sortent intacts dans leur structure.

## 1.4 Périmètre fonctionnel

Import de fichiers EPUB, SRT, DOCX et TXT (les extensions texte annexes `.md`, `.log`, `.text`, `.markdown`, `.rst`, `.asc` sont traitées comme du texte brut) ; détection automatique du format ; segmentation en chunks ; traduction par fournisseur IA local ou cloud ; glossaire et style (manuels, automatiques ou extraits) ; traduction bilingue optionnelle ; passe unique de raffinement ou pipeline multipasse « Raffiner » ; export dans le format d'origine avec préservation de la structure ; reprise après interruption ; interface web (port 5000) et CLI.

## 1.5 Hors périmètre

- Aucun nouveau format d'entrée ou de sortie n'est ajouté au-delà de ceux supportés par TBL.
- Aucune marque d'attribution « TranslateBook », « TBL » ou autre générateur n'est insérée dans les fichiers de sortie (voir chapitre 3).
- Aucun service web dédié, compte utilisateur, ni synchronisation cloud du projet.
- Les fonctionnalités TBL non listées par ce SDD restent disponibles telles quelles tant qu'elles ne contredisent pas un chapitre ci-dessous.

## 1.6 Principes fondateurs

- Un fichier entrant = un fichier sortant dans le même format, structure préservée.
- Le texte source n'est jamais modifié ; seul le résultat traduit est écrit.
- Les checkpoints permettent de reprendre à l'identique après interruption.
- Les clés API ne sont jamais journalisées ni exposées.
- La multipasse « Raffiner » est déclenchée explicitement par l'utilisateur.
- Le fork reste AGPL-3.0 et conserve les avis de licence amonts.

## 1.7 Objectifs qualité

La traduction doit être fidèle, fluide et cohérente sur l'ensemble de l'œuvre. La multipasse « Raffiner » vise un niveau de finition littéraire supérieur au prix d'appels IA supplémentaires. La validation humaine reste la référence finale.

## 1.8 Contrat normatif du produit

**Responsabilités.** Le produit couvre l'import, la segmentation, la traduction, le raffinement (passe unique ou multipasse), l'export préservé et la reprise après interruption.

**Règles métier et invariants.** Les principes de 1.6 s'appliquent à tous les chapitres. Aucune fonctionnalité TBL ne peut être retirée sans modification de ce SDD ; aucune fonctionnalité nouvelle ne peut être ajoutée sans exigence documentée (chapitre 16).

**Préconditions.** L'application démarre avec un fichier d'entrée supporté, un fournisseur configuré (local disponible ou clé API cloud valide) et un modèle accessible.

**Postconditions.** Le fichier de sortie reproduit le format d'entrée avec le contenu traduit ; en mode raffinement, la ou les passes supplémentaires sont appliquées avant l'écriture finale.

**Cas d'erreur.** Format non supporté, fournisseur indisponible, modèle absent, clé API invalide, endpoint refusé, fichier introuvable ou vide, interruption réseau — chaque cas produit un message explicite sans corruption du travail déjà effectué.

**Critères d'acceptation.** Un parcours complet permet d'importer un EPUB/SRT/DOCX/TXT, de le traduire, de l'exporter dans son format et, si demandé, de le raffiner en multipasse sans aucune trace d'attribution TBL dans le fichier produit.

# Chapitre 2 — Fournisseurs IA et référentiel

## 2.1 Objectif

Centraliser la liste des fournisseurs IA supportés, leur configuration et les règles communes d'accès. TBL en fournit déjà la grande majorité ; NovelTrad en ajoute trois.

## 2.2 Fournisseurs conservés du fork TBL

| Fournisseur | Identifiant | Type | Clé API |
|---|---|---|---|
| Ollama | `ollama` | local | non |
| OpenAI / OpenAI-compatible | `openai` | cloud ou local (llama.cpp, LM Studio, vLLM, LocalAI…) | optionnelle |
| Gemini | `gemini` | cloud | oui |
| OpenRouter | `openrouter` | cloud (200+ modèles) | oui |
| Mistral | `mistral` | cloud | oui |
| DeepSeek | `deepseek` | cloud | oui |
| Poe | `poe` | cloud (multi-modèles) | oui |
| NVIDIA NIM | `nim` | cloud | oui |
| LiteLLM | `litellm` | passerelle (CLI) | native par fournisseur |

## 2.3 Fournisseurs ajoutés par NovelTrad

| Fournisseur | Identifiant | Type | Clé API | Endpoint de référence |
|---|---|---|---|---|
| Anthropic (Claude) | `anthropic` | cloud | `ANTHROPIC_API_KEY` | API Anthropic Messages |
| xAI (Grok) | `xai` | cloud | `XAI_API_KEY` | `https://api.x.ai/v1` |
| Nexum Router (dialagram) | `nexum` | cloud (routeur) | `NEXUM_API_KEY` | routeur `dialagram.me` |

Ces trois fournisseurs suivent le même contrat d'adaptateur que les autres (chapitre 2.5) et sont proposés dans l'interface et la CLI au même titre que les fournisseurs hérités.

## 2.4 Configuration

Chaque fournisseur expose : endpoint, modèle, clé API éventuelle (unique ou multiples, séparées par des virgules), fenêtre de contexte, et options spécifiques (ex. désactivation du « thinking »). Les paramètres sont lus depuis `.env` et modifiables à chaud via l'API de paramètres pour les clés figurant dans la liste rechargée.

## 2.5 Contrat commun des fournisseurs

Chaque adaptateur implémente l'abstraction `LLMProvider` du fork TBL :

```python
class LLMProvider(ABC):
    async def generate(self, prompt, timeout, system_prompt) -> Optional[LLMResponse]: ...
    async def get_available_models(self, api_key) -> list: ...   # cloud
```

Règles communes :

- Multi-clés : toute variable `*_API_KEY` accepte une liste séparée par des virgules ; rotation automatique sur HTTP 429 via `KeyPool`.
- Rate-limit : HTTP 429 → rotation de clé ou backoff ; auto-pause configurable ou reprise automatique après `Retry-After`.
- Erreurs : catégories normalisées (timeout, HTTP, JSON, contexte dépassé, inattendu), tentatives limitées par `MAX_TRANSLATION_ATTEMPTS`.
- Aucune clé API n'est journalisée ni envoyée hors du fournisseur concerné.
- `LLM_ENDPOINT_ALLOWLIST` : liste blanche d'hôtes supplémentaires acceptés par le validateur d'endpoint (jamais modifiable depuis le navigateur).

## 2.6 Modèles

L'interface maintient des listes de modèles de repli par fournisseur (dont les gammes Claude pour Anthropic et Grok pour xAI) et interroge, quand c'est possible, l'API `/models` du fournisseur. Les nouveaux fournisseurs doivent fournir leur liste de repli comme les autres.

## 2.7 Invariants

- Une seule configuration active par fournisseur à un instant donné ; le choix du fournisseur détermine la clé et le modèle utilisés.
- Aucun SDK fournisseur n'est requis : les appels passent par `httpx`.
- Un fournisseur local (Ollama) force le parallélisme à 1 ; les fournisseurs cloud peuvent utiliser `PARALLEL_TRANSLATIONS`.

# Chapitre 3 — Suppression de l'attribution TBL

## 3.1 Objectif

Aucun fichier produit par NovelTrad ne doit contenir la marque « TranslateBook », « TBL », ni de lien de générateur. La suppression est complète, dans le code, les tests et les documents.

## 3.2 Éléments supprimés

- `src/config.py` : variables `ATTRIBUTION_ENABLED`, `GENERATOR_NAME`, `GENERATOR_SOURCE`, `ATTRIBUTION_PAGE_ENABLED`.
- `src/core/epub/attribution_page.py` (fichier supprimé) et son appel dans `src/core/epub/translator.py`.
- Métadonnées EPUB : `dc:contributor` (rôle `trl`) et signature `dc:description` « Translated using … ».
- Pied de page TXT « Refined with … » dans `src/core/refine/txt_refiner.py`.
- Commentaire de fin SRT « # Translated with … » dans `src/core/srt_processor.py` et `src/core/adapters/srt_adapter.py`.
- Propriété DOCX `last_modified_by = GENERATOR_NAME` dans `src/core/docx/converter.py` et `src/core/docx/plain_extractor.py`.
- Clés et sections d'attribution dans `.env.example` et les documents `docs/`.
- Tests dédiés : `tests/unit/epub/test_attribution_page.py` et helpers associés dans `tests/unit/epub/conftest.py` ; artefacts dorés régénérés sans entrée `tbl-attribution.xhtml`.

## 3.3 Invariant

Aucune nouvelle forme d'attribution ne peut être réintroduite sans modification préalable de ce SDD. La licence AGPL-3.0 et les notices de copyright amontes demeurent dans le dépôt (chapitre 18) ; seule la marque insérée dans les fichiers de sortie est supprimée.

# Chapitre 4 — Rebranding minimal

## 4.1 Objectif

Renommer les occurrences visibles de l'application vers « NovelTrad », sans refonte de l'interface ni remplacement des assets visuels.

## 4.2 Éléments renommés

- Titre de page web : « Translate Books with LLMs » → « NovelTrad ».
- En-tête d'application : « TBL » → « NovelTrad ».
- Mentions « NovelTrad » dans les messages, journaux et la documentation locale quand elles désignent l'application.

## 4.3 Éléments conservés

- Tous les assets visuels du fork (`src/web/static/img/providers/*.png`, logos, CSS, JS, favicon).
- L'asset `assets/noveltrad.png` du projet NovelTrad historique est conservé à la racine du dépôt.
- Les liens de documentation et de support pointant vers le dépôt amont restent inchangés (source AGPL du fork).

# Chapitre 5 — Architecture logicielle

## 5.1 Vue générale

```
Utilisateur → Interface web (Flask + WebSocket, port 5000)  /  CLI (translate.py)
                            ↓
              src.api.handlers  /  src.core.adapters
                            ↓
        src.core.translator · refine · llm · chunking · glossary · style
                            ↓
              Fournisseurs IA (httpx) · Système de fichiers (checkpoints)
```

## 5.2 Composants principaux (hérités de TBL)

- `translation_api.py` : démarrage du serveur web.
- `src/api/` : routes REST, WebSocket, gestionnaires de tâches, états de traduction.
- `src/core/` : moteur de traduction (`translator.py`, `llm_client.py`, `text_processor.py`, `srt_processor.py`), adaptateurs par format (`epub`, `docx`, `txt`, `srt`, `subtitle`), chunking, glossaire, style, pricing, progress, refine, auto-prep, common.
- `src/web/` : SPA (HTML, CSS, JS), locales i18n (en, fr, de, es, ja, ko, zh-CN, et autres), assets.
- `src/prompts/` : génération des prompts de traduction et de raffinement.
- `src/utils/` : détection de fichiers, sécurité, helpers.
- `translate.py` : interface CLI.

## 5.3 Évolutions d'architecture liées au SDD

- Fournisseurs : ajout des adaptateurs `anthropic`, `xai`, `nexum` dans `src/core/llm/providers/` et `src/core/llm/factory.py` (exigence E-001).
- Multipasse « Raffiner » : extension du pipeline de raffinement (chapitre 9, exigence E-002).
- Suppression du module d'attribution EPUB (chapitre 3).

# Chapitre 6 — Formats d'entrée et préservation

## 6.1 Formats supportés

| Format | Extension | Traitement |
|---|---|---|
| EPUB | `.epub` | extraction XHTML, placeholders, réassemblage, métadonnées |
| SRT | `.srt` | sous-titres par blocs, horodatages préservés |
| DOCX | `.docx` | extraction et réassemblage, préservation du corps |
| TXT | `.txt` | texte brut, découpage en chunks |
| Texte (annexe) | `.md`, `.log`, `.text`, `.markdown`, `.rst`, `.asc` | traités comme TXT |

## 6.2 Principes de préservation

- EPUB : structure du conteneur, ordre de lecture (`spine`), balises et placeholders validés ; réécriture sans perte de structure.
- SRT : indices, horodatages, balises inline et fins de ligne conservés exactement.
- DOCX : corps du document traduit sans altérer la structure.
- TXT : texte Unicode traduit ; encodage de sortie UTF-8.

## 6.3 Détection

La détection utilise l'extension connue puis, à défaut, l'analyse de contenu. Une extension inconnue mais de type texte connue (`.md`, `.log`…) est traitée en TXT. Tout format non supporté est refusé avec un message explicite.

# Chapitre 7 — Pipeline de traduction de base

## 7.1 Objectif

Décrire la passe unique de traduction héritée de TBL, appliquée à chaque chunk.

## 7.2 Étapes

1. Lecture du fichier d'entrée et détection du format.
2. Découpage en chunks (budget `MAX_TOKENS_PER_CHUNK`, découpage intelligent préservant la structure).
3. Construction des prompts (traduction, contexte, placeholders, règles optionnelles).
4. Appel LLM par chunk (parallélisme optionnel pour le cloud, séquentiel pour le local).
5. Validation des placeholders et correction si nécessaire.
6. Réassemblage et écriture du fichier de sortie dans le format d'origine.
7. (Optionnel) marquage de la progression, notifications, estimation des coûts.

## 7.3 Parallélisme

- `PARALLEL_TRANSLATIONS` (défaut 1) : nombre de chunks traduits simultanément.
- Forcé à 1 pour Ollama et autres fournisseurs locaux.
- Borné par `MAX_PARALLEL_TRANSLATIONS` (défaut 16).

## 7.4 Glossaire et style

- Glossaire manuel (JSON/CSV), auto (NER, un appel LLM), injecté par chunk.
- Style : preset manuel, extraction depuis échantillons, ou auto-dérivation depuis le document (un appel LLM).
- Glossaire auto ignoré en mode `--refine-only` ; style auto honoré dans tous les modes.

## 7.5 Bilingue

La sortie bilingue optionnelle présente le texte source et traduit alignés ; les marqueurs SRT associés sont gérés selon la logique TBL.

# Chapitre 8 — Refaire la passe unique de raffinement

## 8.1 Mode raffinage unique (hérité)

TBL propose :

- `--refine` (CLI) : une seconde passe qui polit la traduction (qualité littéraire) — correspond au `refine_after` de l'interface.
- `--refine-only` : ne raffine qu'un fichier déjà traduit (monolingue), sans traduire.
- Zone « Refine » de l'interface : dépôt d'un fichier déjà traduit.
- Mode « Translate + Refine » : traduction puis raffinement.

Le prompt de raffinement est généré par `generate_refinement_prompt` (et sa variante sous-titres), avec contexte du bloc précédent raffiné, glossaire et instructions de style.

## 8.2 Invariants du mode unique

- Le raffinement est monolingue : la langue cible est la langue du fichier.
- Les placeholders et leur position exacte sont conservés.
- En mode `refine_after`, la barre de progression est en deux phases (0–50 %, 50–100 %).

# Chapitre 9 — Pipeline multipasse « Raffiner » (exigence E-002)

## 9.1 Objectif

Quand l'utilisateur choisit « Raffiner », NovelTrad exécute un pipeline multipasse après la traduction. Ce pipeline remplace la passe unique de raffinement par quatre passes séquentielles, chacune produisant une sortie intermédiaire et alimentant la suivante.

## 9.2 Définition des quatre passes

| Passe | Nom | Entrée | Sortie | Rôle |
|---|---|---|---|---|
| 1 | Traduction | source | brouillon traduit | passe unique existante (chapitre 7) |
| 2 | Vérification de contexte | brouillon traduit + contexte voisin | notes/rapport de contexte | cohérence avec le contexte précédent/suivant, terminologie, continuité |
| 3 | Raffinement (orthographe, grammaire, fluidité) | brouillon traduit | texte corrigé | corrections linguistiques sans changement de sens |
| 4 | Production du texte final | brouillon traduit + notes des passes 2 et 3 | texte final | fusionne la traduction et les informations des passes 2 et 3 en un texte final prêt à l'emploi |

La passe 4 « sort le texte final à partir de la traduction et des informations des passes 2 et 3 » : elle reçoit le brouillon de la passe 1, le rapport de contexte de la passe 2 et le texte corrigé de la passe 3, et produit le texte définitif.

## 9.3 Déclenchement

- Interface : cocher « Raffiner » (mode Translate + Raffiner multipasse).
- CLI : `--refine` active la multipasse (au lieu de la passe unique historique), `--refine-only` applique les passes 2–4 à un fichier déjà traduit.

## 9.4 Prompts

Quatre jeux de prompts versionnés, un par passe, générés dans `src/prompts/` :

- `PASS 1 — TRANSLATE` : prompt de traduction existant.
- `PASS 2 — CONTEXT` : analyse de cohérence avec le contexte voisin ; sortie structurée (notes).
- `PASS 3 — REFINE` : corrections orthographe/grammaire/ponctuation/fluidité.
- `PASS 4 — FINAL` : rédaction finale combinant la traduction et les informations des passes 2 et 3.

Chaque prompt impose la préservation des placeholders et de la structure du format.

## 9.5 États, checkpoints et reprise

- Chaque passe dispose de son propre état de progression et de son checkpoint.
- Une interruption permet de reprendre à la passe et au chunk courants, sans rejouer les passes déjà terminées.
- Le pipeline multipasse réutilise le mécanisme de checkpoint TBL (plain-text checkpoint) en l'étendant à la passe 4.

## 9.6 Progression

La barre de progression annonce le nombre total de passes et reflète la passe courante et le chunk courant. Les phases sont étiquetées (Traduction / Contexte / Raffinement / Final).

## 9.7 Invariants

- Les passes sont strictement ordonnées 1 → 2 → 3 → 4 ; aucune ne peut être sautée ni désordonnée.
- Aucune passe ne modifie le fichier source.
- Les placeholders et la structure du format sont préservés sur toutes les passes.
- Le nombre de passes est fixé à 4 ; toute évolution passe par une modification de ce SDD.

# Chapitre 10 — Glossaire et style

## 10.1 Glossaire

- Sources : fichier JSON/CSV, auto-extraction NER, saisie manuelle.
- Application : injection par chunk dans le prompt ; cohérence des entités nommées sur toute l'œuvre.
- En mode multipasse, le glossaire est appliqué à la passe 1 et pris en compte dans les passes 2 et 4.

## 10.2 Style

- Presets : extraction depuis des livres échantillons ou écriture manuelle.
- Application : bloc de style inséré dans les prompts de traduction et de raffinement.
- Auto-style : un appel LLM dérive le style depuis le document ; honoré en mode traduction, raffinement et refine-only.

## 10.3 Invariants

- Aucun contenu de glossaire ou de style n'est appliqué en l'absence de consentement utilisateur (choix explicite ou option `--auto-*`).
- Les données de glossaire/style ne sont jamais persistées automatiquement dans un emplacement non annoncé.

# Chapitre 11 — Fonctionnalités héritées conservées

Toutes les fonctionnalités suivantes de TBL restent actives et inchangées, sous réserve des chapitres 3, 4 et 9 :

- **Reprise après interruption** : `CheckpointManager`, reprise à l'index courant, `resume-manager.js`.
- **Parallélisme** : exécution ordonnée et concurrente pour le cloud.
- **Notifications** : webhooks (ntfy, gotify, Discord, Slack, HTTP) sur succès, échec ou interruption.
- **Estimation des coûts** : `src/core/pricing/`, estimation d'entrée/sortie par modèle.
- **TTS** : génération audio Edge-TTS optionnelle (CLI).
- **Nettoyage de texte** : correction OCR/typographique pendant la traduction (`--text-cleanup`).
- **Détection du « thinking »** : classification des modèles, paramètres `think`, avertissements.
- **Optimisation adaptative du contexte** : `AUTO_ADJUST_CONTEXT`, pas de croissance du contexte.
- **API de test rapide** (`quick-test`) et **pré-vol** (`preflight`) : vérification de la configuration avant lancement.

# Chapitre 12 — Interface web

## 12.1 Vue générale

SPA servie par Flask sur le port 5000, communication via REST et WebSocket (Socket.IO). L'interface est multilingue (i18n) avec des locales complètes en français et anglais et des traductions secondaires.

## 12.2 Écrans et zones

- Zone de dépôt principale (traduction) et zone secondaire (raffinement).
- Choix du fournisseur, de l'endpoint, de la clé API, du modèle, du nombre de requêtes parallèles, des options.
- Options de glossaire et de style (sélecteurs, auto, extraits).
- Mode bilingue, mode Raffiner (multipasse), texte de nettoyage.
- Barre de progression, journal des messages, statut du fournisseur, boutons Interrompre / Reprendre.
- Estimation des coûts, modèles disponibles, test de connexion.

## 12.3 Exigences UI des nouveaux fournisseurs

- Le menu déroulant « AI Provider » propose `Anthropic`, `xAI` et `Nexum` comme les autres fournisseurs.
- Les champs clé API/modèle associés s'affichent selon le fournisseur sélectionné.
- Les listes de modèles de repli incluent Claude (Anthropic) et Grok (xAI).

## 12.4 Invariants

- Aucune clé API n'est affichée en clair après saisie.
- Aucune logique métier dans le front ; toutes les actions passent par l'API.

# Chapitre 13 — Interface CLI

## 13.1 Commandes

- `python translate.py -i <fichier> -sl <source> -tl <cible> -m <modèle> --provider <fournisseur>`
- Options héritées : `--parallel`, `--text-cleanup`, `--refine`, `--refine-only`, `--glossary`, `--auto-glossary`, `--auto-style`, `--tts`, etc.

## 13.2 Évolutions CLI

- Nouveaux fournisseurs : `--provider anthropic|xai|nexum` avec leurs clés respectives (`--anthropic_api_key`, `--xai_api_key`, `--nexum_api_key`).
- `--refine` déclenche le pipeline multipasse du chapitre 9.
- `--refine-only` applique les passes 2 à 4 à un fichier déjà traduit.

# Chapitre 14 — Déploiement et environnement

## 14.1 Démarrage

- Windows : `start.bat` (ou `TranslateBook.exe` dans les builds).
- macOS : `./start.sh`.
- Docker : `docker build -t translatebook . && docker run -p 5000:5000 …` ou `docker-compose up`.

## 14.2 Environnement

- `.env` copié depuis `.env.example` ; variables de fournisseur, performance, notifications, attribution supprimée (chapitre 3).
- Données persistantes : dossier `TranslateBook_Data` / dossier de travail local ; fichiers traduits écrits à l'emplacement configuré.

## 14.3 Options d'exploitation

| Variable | Rôle | Défaut |
|---|---|---|
| `PORT` | port du serveur web | `5000` |
| `REQUEST_TIMEOUT` | timeout des appels LLM | `300` |
| `MAX_TOKENS_PER_CHUNK` | budget de découpage | `450` |
| `PARALLEL_TRANSLATIONS` | parallélisme cloud | `1` |
| `AUTO_PAUSE_ON_RATE_LIMIT` | pause auto sur 429 | `true` |
| `GEMINI_SAFETY_THRESHOLD` | filtre Gemini | `BLOCK_NONE` |
| `LLM_ENDPOINT_ALLOWLIST` | hôtes autorisés supplémentaires | vide |

# Chapitre 15 — Sécurité

## 15.1 Clés API

- Jamais journalisées ni affichées ; stockées en variables d'environnement ou transmises sécurisées.
- Multi-clés séparées par des virgules ; rotation automatique sur 429.
- Envoi uniquement au fournisseur concerné.

## 15.2 Endpoints

- Le validateur refuse les endpoints inconnus sauf si présents dans `LLM_ENDPOINT_ALLOWLIST`.
- La liste blanche n'est jamais modifiable depuis le navigateur.
- Aucune redirection vers un endpoint non autorisé.

## 15.3 Exfiltration

- Le garde d'endpoint empêche l'envoi de la clé d'un fournisseur vers un hôte non déclaré.
- Les prompts ne contiennent que le texte à traduire et les instructions ; aucun secret.

# Chapitre 16 — Exigences (EF) et traçabilité

## 16.1 Exigences fonctionnelles

| ID | Exigence |
|---|---|
| EF-001 | Importer EPUB, SRT, DOCX et TXT (+ extensions texte annexes) et détecter le format |
| EF-002 | Traduire un fichier avec le fournisseur, le modèle et l'endpoint configurés |
| EF-003 | Reprendre une traduction interrompue au dernier checkpoint |
| EF-004 | Appliquer un glossaire et/ou un style (manuel, auto, extrait) |
| EF-005 | Produire une sortie bilingue optionnelle |
| EF-006 | Appliquer une passe unique de raffinement (`--refine` historique / refine_after) |
| EF-007 | Exécuter le pipeline multipasse « Raffiner » : traduction → contexte → raffinement → final |
| EF-008 | Exécuter la multipasse en `--refine-only` sur un fichier déjà traduit |
| EF-009 | Prendre en charge Anthropic (Claude), xAI (Grok) et Nexum Router en plus des fournisseurs hérités |
| EF-010 | Ne jamais insérer de marque d'attribution TBL dans les fichiers de sortie |
| EF-011 | Afficher une interface web multilingue avec progression, journal et contrôle Interrompre/Reprendre |
| EF-012 | Traduire depuis la CLI avec toutes les options documentées |
| EF-013 | Estimer les coûts et détecter les modèles disponibles par fournisseur |
| EF-014 | Notifier par webhook en fin de traduction (succès/échec/interruption) |
| EF-015 | Préserver la structure du format d'entrée (EPUB/SRT/DOCX/TXT) dans la sortie |
| EF-016 | Nettoyer les défauts OCR/typographiques en traduction (`--text-cleanup`) |

## 16.2 Règles métier

| ID | Règle |
|---|---|
| RM-001 | Le fichier source n'est jamais modifié |
| RM-002 | La sortie reproduit le format d'entrée |
| RM-003 | Les clés API ne sont jamais journalisées ni exposées |
| RM-004 | La multipasse est strictement ordonnée 1→2→3→4 et ne saute aucune passe |
| RM-005 | La passe 4 utilise la traduction ET les informations des passes 2 et 3 |
| RM-006 | Une interruption reprend à la passe et au chunk courants |
| RM-007 | Aucune attribution TBL dans les fichiers de sortie |
| RM-008 | Le parallélisme est forcé à 1 pour les fournisseurs locaux |
| RM-009 | Aucun endpoint hors liste blanche n'est appelé avec une clé |
| RM-010 | Les assets visuels du fork et `assets/noveltrad.png` sont conservés |

## 16.3 Traçabilité

La matrice de traçabilité relie chaque exigence aux modules, tests et sections du SDD ; elle est tenue à jour à chaque évolution. Les identifiants EF/RM sont stables et uniques.

# Chapitre 17 — Tests et critères d'acceptation

## 17.1 Suite héritée

Toute la suite `pytest` de TBL est conservée. La suppression de l'attribution (chapitre 3) impose la régénération des artefacts dorés et la suppression des tests dédiés ; aucun test restant ne doit dépendre de l'attribution.

## 17.2 Tests à prévoir pour les évolutions

| ID | Objet | Critère |
|---|---|---|
| UT-PROV-001 | Adaptateurs Anthropic/xAI/Nexum | réponse `LLMResponse` normalisée, erreurs classifiées, rotation de clé |
| IT-PROV-002 | Modèles listés par les nouveaux fournisseurs | `get_available_models` fonctionne ou retourne la liste de repli |
| UT-MULTI-001 | Prompts des 4 passes | chaque prompt impose la préservation des placeholders |
| IT-MULTI-002 | Multipasse complète | ordre 1→2→3→4, sortie de la passe 4 = texte final |
| IT-MULTI-003 | Reprise en multipasse | interruption/reprise à la passe courante sans rejeu |
| UT-ATTR-001 | Aucune attribution | les fichiers produits (EPUB/TXT/SRT/DOCX) ne contiennent aucune chaîne TBL/TranslateBook |
| FT-UI-001 | Nouveaux fournisseurs dans l'interface | menu, champs clé/modèle, listes de repli |

## 17.3 Critères d'acceptation généraux

- Le serveur démarre sur le port 5000 sans erreur.
- Les fichiers de sortie sont exempts de marque d'attribution.
- Les nouveaux fournisseurs fonctionnent avec une clé valide ; sans clé, erreur explicite.
- La multipasse produit un fichier final plus cohérent que la passe unique (contrôle humain).

# Chapitre 18 — Licence, provenance et conformité

## 18.1 Licence

NovelTrad et son implémentation sont distribués sous `AGPL-3.0-only`, héritée du projet amont TranslateBooksWithLLMs (AGPL-3.0). Le fichier `LICENSE` et les en-têtes de copyright des fichiers repris sont conservés.

## 18.2 Provenance du fork

- Dépôt amont : `https://github.com/hydropix/TranslateBooksWithLLMs`.
- Fork : `Balrog57/noveltrad` (GitHub), cloné localement.
- Toute mise à jour amont est évaluée avant intégration ; elle n'est jamais absorbée automatiquement si elle contredit ce SDD.

## 18.3 Obligations

- La suppression de l'attribution de sortie (chapitre 3) ne supprime ni la licence AGPL-3.0, ni les avis de copyright amonts, ni l'obligation de fournir le code source.
- Les nouveaux modules (providers, multipasse) sont écrits sous AGPL-3.0 ou réutilisent du code compatible en conservant ses avis.

# Chapitre 19 — Annexes techniques

## 19.1 Glossaire

| Terme | Définition |
|---|---|
| Chunk | segment de texte traduit en un appel LLM |
| Passe | étape du pipeline (traduction, contexte, raffinement, final) |
| Checkpoint | état persistant permettant la reprise après interruption |
| Provider | fournisseur IA (local ou cloud) |
| Placeholder | jeton protégé représentant une balise/structure à préserver |
| Refine | option de raffinement ; en multipasse, pipeline des 4 passes |

## 19.2 Arborescence de référence

L'arborescence est celle du fork TBL. Les ajouts NovelTrad se limitent à :

- `src/core/llm/providers/anthropic.py`, `xai.py`, `nexum.py` (E-001) ;
- l'extension du pipeline de raffinement en `src/core/refine/` et `src/prompts/` (E-002) ;
- la suppression du module d'attribution (chapitre 3) ;
- `NovelTrad_SDD.md` et `assets/noveltrad.png` à la racine.

## 19.3 Journal des décisions

| Date | Décision | Justification |
|---|---|---|
| 2026-08-09 | Repartir du fork TranslateBooksWithLLMs et vider l'implémentation Streamlit historique | TBL couvre ~99 % du périmètre ; l'implémentation précédente est abandonnée pour la 5ᵉ fois au profit d'un socle éprouvé |
| 2026-08-09 | Ajouter Anthropic (Claude), xAI (Grok) et Nexum Router | couvrir les fournisseurs manquants demandés |
| 2026-08-09 | Définir le pipeline multipasse « Raffiner » en 4 passes (traduction, contexte, raffinement, final) | produire un texte final à partir de la traduction et des informations des passes de contrôle |
| 2026-08-09 | Supprimer complètement l'attribution TBL des fichiers de sortie | aucune marque de générateur souhaitée ; la licence AGPL reste conservée |
| 2026-08-09 | Rebrand minimal « NovelTrad » (noms uniquement) et conservation des assets | identité sans refonte de l'interface |

## 19.4 Clôture

Le présent document est la référence technique unique de NovelTrad. Toute évolution fonctionnelle, tout fournisseur ou toute passe supplémentaire modifie directement ce document avant toute implémentation.
