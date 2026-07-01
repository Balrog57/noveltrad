# Volume 18 — Journalisation

## 18.1 Niveaux de log

| Niveau | Usage |
|--------|-------|
| DEBUG | Détails des appels IA, tokens, temps |
| INFO | Actions utilisateur, démarrage, export |
| WARN | Retry, dégradations |
| ERROR | Échecs agent, crash |

## 18.2 Destinations

- Fichier `logs/app.log` dans le répertoire utilisateur global.
- Fichier `logs/` dans le projet actif.
- Console en mode dev.
- Écran Console dans l’UI.

## 18.3 Rotation

- Rotation quotidienne.
- Conservation 7 jours pour les logs globaux, 30 jours pour les logs projet.

## 18.4 Crash reports

- `process.on('uncaughtException', ...)` capture les erreurs fatales.
- Fichier `crash-reports/` avec stack trace et version.
- Option d’envoi automatique (opt-in).

## 18.5 Performance profiling

- Mesure du temps par étape workflow.
- Comptage des tokens consommés.
- Métriques mémoire.
- Export CSV de statistiques.

## 18.6 Format des logs

Les logs sont écrits au format **JSON structuré** dans les fichiers, et au format lisible dans la Console UI.

### Exemple de ligne JSON (fichier)

```json
{
  "timestamp": "2026-06-30T14:32:01.123Z",
  "level": "INFO",
  "component": "WorkflowEngine",
  "correlationId": "job_abc123",
  "message": "Workflow step translate completed",
  "durationMs": 12450,
  "tokensIn": 2048,
  "tokensOut": 512
}
```

### Exemple de ligne lisible (Console UI)

```text
[2026-06-30 14:32:01] [INFO] [WorkflowEngine] Workflow step translate completed (12.45 s, 2048→512 tokens)
```

### Champs obligatoires

| Champ | Description |
|---|---|
| `timestamp` | Date/heure ISO 8601 UTC |
| `level` | DEBUG / INFO / WARN / ERROR |
| `component` | Nom du module/agent |
| `message` | Message court |
| `correlationId` | ID de job ou de requête (permet de suivre un workflow) |

### Champs optionnels

| Champ | Usage |
|---|---|
| `durationMs` | Temps d'exécution d'une étape |
| `tokensIn` / `tokensOut` | Consommation IA |
| `error` | Stack trace en cas d'erreur |
| `projectId` / `chapterId` | Contexte métier |

**Règles.**
- Jamais inclure de clé API, mot de passe ou donnée personnelle dans un log.
- Tronquer les prompts très longs si nécessaire (limiter à 1 000 caractères dans les logs UI).
- Utiliser le même objet log pour le fichier et la Console ; le renderer formate pour l'affichage.
## ✅ Critères d’acceptation de la journalisation

- [ ] Les 4 niveaux de log sont configurables.
- [ ] Les logs projet sont isolés par projet.
- [ ] Les erreurs fatales génèrent un crash report.
- [ ] La Console UI affiche les logs en temps réel.
- - [ ] Les métriques de performance sont collectées.
- [ ] Les logs fichiers utilisent le format JSON structuré avec 	imestamp, level, component, message et correlationId.
- [ ] Aucune clé API ni donnée sensible n'apparaît dans les logs.
