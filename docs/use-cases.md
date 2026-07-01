# Cas d'usage

NovelTrad 2.0 s'adresse à plusieurs profils et types de projets. Cette page détaille les scénarios d'usage les plus fréquents.

---

## 1. Traduction de web novels chinois/coréens/japonais

### Profil

Traducteur amateur de web novels vers le français ou l'anglais.

### Besoins

- Gérer des centaines de chapitres sans perdre la cohérence.
- Garantir la traduction stable des noms propres et des termes propres à l'univers.
- Produire un EPUB lisible sans repasser sur chaque chapitre.

### Workflow NovelTrad

```text
Créer un projet par roman
    ↓
Importer les chapitres (TXT / Markdown / EPUB source)
    ↓
Laisser l'extraction automatique proposer les termes candidats
    ↓
Valider / corriger le lexique (noms, lieux, techniques)
    ↓
Lancer la traduction chapitre par chapitre ou en lot
    ↓
Vérifier le score qualité et le rapport de cohérence
    ↓
Exporter en EPUB ou HTML
```

### Config recommandée

- **Modèle qualité** : `qwen3.5:9b`
- **Modèle rapide** : `qwen3.5:4b`
- **Paire de langues** : `zh-fr`, `ko-fr`, `ja-fr`

### Valeur ajoutée

La Translation Memory réutilise les phrases déjà traduites dès le chapitre 2, ce qui réduit les appels IA et améliore la cohérence stylistique sur la durée.

---

## 2. Relecture et édition de fan-fictions

### Profil

Éditeur de fan-fiction souhaitant industrialiser la relecture et harmoniser le style.

### Besoins

- Détecter les incohérences dans un texte déjà traduit.
- Standardiser les termes (noms de personnages, lieux magiques, etc.).
- Obtenir un score qualité objectif avant publication.

### Workflow NovelTrad

```text
Importer la fan-fiction existante
    ↓
Créer le lexique avec les termes de l'univers
    ↓
Lancer le workflow à partir de l'étape "cohérence" ou "style"
    ↓
Utiliser les agents Grammaire, Style et Polish pour améliorer
    ↓
Valider le QA score
    ↓
Exporter vers DOCX ou EPUB
```

### Config recommandée

- **Modèle qualité** : `qwen3.5:9b` ou `deepseek-r1:7b`
- **Modèle rapide** : optionnel
- **Mode** : reprise partielle (`startStage: 'style'`)

### Valeur ajoutée

Les agents de cohérence et de qualité fournissent un rapport chiffré, ce qui transforme la relecture subjective en processus vérifiable.

---

## 3. Traduction par lots de fichiers EPUB

### Profil

Équipe de traduction ou utilisateur voulant traiter plusieurs livres ou arcs narratifs d'un coup.

### Besoins

- Traiter plusieurs chapitres ou fichiers sans supervision constante.
- Reprendre après une interruption.
- Exporter chaque fichier individuellement.

### Workflow NovelTrad

```text
Créer un projet
    ↓
Importer plusieurs EPUB ou chapitres
    ↓
Configurer le provider IA et les modèles
    ↓
Sélectionner les chapitres dans l'UI
    ↓
Lancer le traitement par lots
    ↓
Surveiller la file d'attente en temps réel
    ↓
Exporter tous les chapitres traduits
```

### Config recommandée

- **Concurrence** : `maxConcurrentJobs: 1` (modèle local Ollama)
- **Retry** : `maxRetries: 2`
- **Batch** : 5 à 10 chapitres selon la taille

### Valeur ajoutée

Le Workflow Engine gère la file d'attente, la persistance SQLite et la reprise après interruption. Un chapitre en échec ne bloque pas le lot entier.

---

## 4. Collaboration multi-utilisateurs (v2.0+)

### Profil

Équipe de traduction collaborative.

### Besoins

- Partager lexique, mémoire et traductions.
- Fusionner plusieurs versions d'un chapitre.
- Suivre l'historique des modifications.

### Workflow NovelTrad (futur)

```text
Projet partagé via Git ou cloud
    ↓
Chaque traducteur travaille sur des chapitres attribués
    ↓
Lexique et TM synchronisés
    ↓
Merge des traductions avec historique et diff
    ↓
QA final et export commun
```

### Valeur ajoutée

La base SQLite + fichiers projet autonomes facilitent le partage. L'historique des versions permet le rollback et le merge.

---

## 5. Mode local et confidentialité totale

### Profil

Utilisateur ne voulant aucune donnée dans le cloud.

### Besoins

- 100 % offline.
- Pas d'API cloud obligatoire.
- Modèles locaux via Ollama.

### Workflow NovelTrad

```text
Installer Ollama localement
    ↓
Télécharger qwen3.5:9b et qwen3.5:4b
    ↓
Configurer NovelTrad avec provider "Ollama"
    ↓
Tout le reste reste local
```

### Valeur ajoutée

Aucune donnée source ou traduite ne quitte la machine. La base SQLite et les fichiers projet restent sur le disque local.

---

## 6. Apprentissage et fine-tuning (v2.0+)

### Profil

Utilisateur avancé voulant améliorer la qualité sur un corpus spécifique.

### Besoins

- Exporter le corpus projet (source + cible).
- Fine-tuner un modèle local.
- Réintégrer le modèle affiné dans NovelTrad.

### Workflow NovelTrad

```text
Traduire 10+ chapitres avec le pipeline par défaut
    ↓
Exporter la TM au format TMX ou JSON
    ↓
Fine-tuner un modèle Ollama compatible (LoRA/QLoRA)
    ↓
Enregistrer le modèle affiné comme provider personnalisé
    ↓
Utiliser le modèle affiné pour les chapitres suivants
```

### Valeur ajoutée

La TM et le lexique forment déjà un corpus structuré. L'intégration future de fine-tuning permettra d'adapter le style au roman.

---

## 7. Relecture QA assistée

### Profil

Traducteur voulant valider et corriger systématiquement une traduction existante.

### Besoins

- Identifier automatiquement les erreurs courantes.
- Mettre en file d'attente les segments suspects.
- Corriger par lots.

### Workflow NovelTrad

```text
Importer la traduction
    ↓
Lancer l'agent ConsistencyAgent
    ↓
Lancer l'agent QAAgent
    ↓
Consulter la file d'attente QA
    ↓
Corriger les segments marqués
    ↓
Relancer les étapes concernées (retryStep)
    ↓
Valider et exporter
```

### Inspiration

[NovelTrans](https://github.com/YuBing-link/noveltrans) formalise cette file d'attente QA par épisode. NovelTrad la reproduit via les tables `jobs` et `job_steps` et les méthodes `retryStep` / `retryFrom`.

---

## 8. Glossaire verrouillé pour longue série

### Profil

Traducteur d'une série de 500+ chapitres voulant garantir la cohérence des noms propres.

### Besoins

- Verrouiller les traductions des personnages, lieux, techniques.
- Interdire certaines traductions (termes "forbidden").
- Détecter automatiquement les alias.

### Workflow NovelTrad

```text
Extraire automatiquement les termes candidats
    ↓
Valider le lexique (locked=true pour les noms propres)
    ↓
Ajouter des termes "forbidden" si nécessaire
    ↓
Lancer la traduction — LexiconAgent applique impérativement
    ↓
Contrôler les substitutions dans le rapport
```

### Inspiration

[OmegaT](https://omegat.org/) et [Glossarion](https://github.com/Shirochi-stack/Glossarion) montrent que le glossaire verrouillé est un must-have pour la cohérence sur les longs romans.

---

## Tableau récapitulatif

| Cas d'usage | Priorité | Modèle qualité | Mode batch | Plugins |
|---|---|---|---|---|
| Web novels | Must | `qwen3.5:9b` | Oui | Non |
| Fan-fictions | Must | `qwen3.5:9b` | Non | Non |
| EPUB batch | Should | `qwen3.5:9b` | Oui | Export EPUB |
| Collaboration | v2.0+ | selon projet | Oui | Sync |
| 100 % local | Must | Ollama local | Oui | Non |
| Fine-tuning | v2.0+ | modèle affiné | Non | Training |
| Relecture QA | Should | `qwen3.5:9b` | Non | Non |
| Glossaire verrouillé | Must | `qwen3.5:9b` | Oui | Non |

---

## Mapping avec les volumes du SDD

| Cas d'usage | Volumes concernés |
|---|---|
| Traduction de web novels | [00-Vision](/volumes/00-Vision), [02-Installation](/volumes/02-Installation), [03-AI-Models](/volumes/03-AI-Models), [05-Project-Management](/volumes/05-Project-Management), [07-Workflow](/volumes/07-Workflow), [09-Translation-Memory](/volumes/09-Translation-Memory), [10-Lexicon](/volumes/10-Lexicon), [13-Export](/volumes/13-Export) |
| Relecture de fan-fictions | [05-Project-Management](/volumes/05-Project-Management), [07-Workflow](/volumes/07-Workflow), [11-Consistency](/volumes/11-Consistency), [12-Quality](/volumes/12-Quality), [13-Export](/volumes/13-Export) |
| Traduction par lots de fichiers EPUB | [05-Project-Management](/volumes/05-Project-Management), [07-Workflow](/volumes/07-Workflow), [13-Export](/volumes/13-Export), [22-Performance](/volumes/22-Performance) |
| Collaboration multi-utilisateurs | [05-Project-Management](/volumes/05-Project-Management), [14-History](/volumes/14-History), [16-Internal-API](/volumes/16-Internal-API), [24-Development-Plan](/volumes/24-Development-Plan) |
| Mode local et confidentialité | [02-Installation](/volumes/02-Installation), [03-AI-Models](/volumes/03-AI-Models), [21-Security](/volumes/21-Security) |
| Apprentissage et fine-tuning | [09-Translation-Memory](/volumes/09-Translation-Memory), [12-Quality](/volumes/12-Quality), [24-Development-Plan](/volumes/24-Development-Plan) |
| Relecture QA assistée | [07-Workflow](/volumes/07-Workflow), [11-Consistency](/volumes/11-Consistency), [12-Quality](/volumes/12-Quality) |
| Glossaire verrouillé pour longue série | [07-Workflow](/volumes/07-Workflow), [10-Lexicon](/volumes/10-Lexicon), [11-Consistency](/volumes/11-Consistency) |
## Exemple concret : chapitre 1 d'une web novel chinoise

### Avant

Un fichier `chapitre_01.txt` avec 50 paragraphes, des noms propres non traduits, pas de mémoire.

### Après NovelTrad

- Lexique auto-extrait : `Lin Ming`, `Azure Sky Continent`, `Qi Condensation`.
- Traduction avec mémoire et lexique verrouillés.
- Score qualité : 87/100.
- Corrections manuelles sur 3 paragraphes.
- Export EPUB prêt à publier.

### Temps estimé

- Configuration initiale : 10 min.
- Traduction chapitre 1 : 5 min (Ollama local).
- Vérification + corrections : 10 min.
- Total : ~25 min pour un chapitre.

---

## Pour aller plus loin

- [Volume 0 — Vision](/volumes/00-Vision)
- [Volume 7 — Workflow](/volumes/07-Workflow)
- [Volume 10 — Lexique](/volumes/10-Lexicon)
- [Volume 13 — Export](/volumes/13-Export)
- [Guide développeur](/developer-guide)
- [Projets similaires et inspirations](/inspirations)
