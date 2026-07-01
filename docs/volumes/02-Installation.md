# Volume 2 — Installation et premier lancement

## Objectif

L’utilisateur télécharge l’installeur, lance NovelTrad 2.0, et l’application le guide jusqu’à ce qu’un premier projet puisse être créé. Aucune ligne de commande n’est requise.

## Flux du premier lancement

```text
Bienvenue
    ↓
Vérification
    ✓ Ollama installé ?
    Sinon → Installer Ollama
    ↓
Vérification modèle IA
    ✓ Modèle requis présent ?
    Sinon → Télécharger le modèle
    ↓
Configuration rapide
    Langue source, langue cible, dossier par défaut
    ↓
Test de connexion
    ↓
Application prête
```

**Note.** NovelTrad 2.0 utilise exclusivement Ollama comme moteur IA local. Il n’y a pas de dépendance NLLB ni de backend Python. Le modèle de pré-traduction est un modèle Ollama léger (ex. `qwen3.5:4b`), pas un modèle NLLB séparé.

## 2.1 Détection d’Ollama

**Méthode.** Requête HTTP `GET http://localhost:11434/api/tags`.

```typescript
import { Ollama } from 'ollama'

async function isOllamaRunning(host = 'http://localhost:11434'): Promise<boolean> {
  try {
    const ollama = new Ollama({ host })
    await ollama.list()
    return true
  } catch {
    return false
  }
}
```

**Référence** (Context7: `/ollama/ollama-js`) : `ollama.list()` retourne les modèles disponibles ; une erreur indique que le serveur n’est pas accessible.

## 2.2 Installation d’Ollama

### Windows

1. Télécharger `OllamaSetup.exe` depuis `https://ollama.com/download`.
2. Exécuter silencieusement si possible : `OllamaSetup.exe /S`.
3. Attendre que le service réponde sur `localhost:11434` (timeout 5 minutes).

### macOS

1. Télécharger le `.dmg`.
2. Monter et copier `Ollama.app` dans `/Applications`.
3. Lancer l’application et attendre le démarrage du serveur.

### Linux

1. Exécuter : `curl -fsSL https://ollama.com/install.sh | sh`.
2. Attendre le démarrage du service systemd.

**Note.** L’installeur Ollama est téléchargé depuis le site officiel. NovelTrad ne redistribue pas Ollama.

## 2.3 Détection et téléchargement du modèle

### Modèle par défaut

| Usage | Modèle recommandé | Taille | Raison |
|-------|-------------------|--------|--------|
| Pré-traduction rapide | `qwen3.5:4b` ou `llama3.2:3b` | ~3 GB | Rapide, multilingue, contexte 256K |
| Traduction qualitative | `qwen3.5:9b` ou `deepseek-r1:7b` | ~6–7 GB | Meilleur style, support 256K |

L’utilisateur peut changer le modèle par défaut dans l’écran Paramètres.

### Téléchargement avec progression

```typescript
import { Ollama } from 'ollama'

async function* pullModelProgress(name: string, host = 'http://localhost:11434') {
  const ollama = new Ollama({ host })
  const stream = await ollama.pull({ model: name, stream: true })
  for await (const chunk of stream) {
    yield chunk // { status, completed?, total? }
  }
}
```

**Référence** (Context7: `/ollama/ollama-js`) : `ollama.pull({ model, stream: true })` retourne un flux async iterable ; afficher `completed/total` pour la barre de progression.

## 2.4 Validation

Avant de quitter le wizard :

1. `ollama.list()` confirme le modèle présent.
2. Un appel test de chat (`ollama.chat`) avec un prompt court retourne une réponse non vide.
3. L’utilisateur peut cliquer sur *Terminer*.

## 2.5 Écran de bienvenue

### Wireframe

```text
┌─────────────────────────────────────┐
│         🚀 NovelTrad 2.0            │
│                                     │
│  Bienvenue dans l’assistant de        │
│  traduction assistée par IA.          │
│                                     │
│  [ Suivant ]                        │
│                                     │
└─────────────────────────────────────┘
```

```text
┌─────────────────────────────────────┐
│  Vérification d’Ollama              │
│                                     │
│  ✓ Ollama détecté                   │
│  ○ Téléchargement de qwen3.5:4b…    │
│    [████████████░░░░] 67 %          │
│                                     │
│  [ Suivant ] (désactivé)            │
└─────────────────────────────────────┘
```

## 2.6 Stockage des préférences de premier lancement

Les choix du wizard sont persistés dans :

- `%APPDATA%/NovelTrad/config.json` (Windows)
- `~/Library/Application Support/NovelTrad/config.json` (macOS)
- `~/.config/NovelTrad/config.json` (Linux)

```json
{
  "firstRunCompleted": true,
  "ollamaHost": "http://localhost:11434",
  "defaultModel": "qwen3.5:9b",
  "defaultPreTranslateModel": "qwen3.5:4b",
  "sourceLanguage": "zh",
  "targetLanguage": "fr",
  "defaultProjectsPath": "~/NovelTrad Projects"
}
```

## ✅ Critères d’acceptation de l’installation

- [ ] Sur une machine sans Ollama, l’assistant télécharge et installe Ollama automatiquement.
- [ ] Le modèle par défaut est téléchargé avec une barre de progression.
- [ ] Le wizard refuse de passer à l’étape suivante si le test de connexion échoue.
- [ ] Les préférences sont persistées et relues au lancement suivant.
- [ ] L’utilisateur peut relancer le wizard depuis Paramètres.
