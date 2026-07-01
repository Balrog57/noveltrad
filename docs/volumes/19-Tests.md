# Volume 19 — Tests

## 19.1 Stratégie globale

| Type | Outil | Portée |
|------|-------|--------|
| Unitaires | Vitest | Services, managers, repositories |
| Intégration | Vitest | Workflow complet avec mocks IA |
| E2E | Playwright | Parcours utilisateur réels |
| Performance | Vitest + benchmarking | Temps de parsing, d’export |
| Régression | GitHub Actions | Suite complète à chaque PR |

## 19.2 Tests unitaires

Exemple : `ConsistencyChecker`

```typescript
import { describe, it, expect } from 'vitest'
import { ConsistencyChecker } from '../services/ConsistencyChecker'

describe('ConsistencyChecker', () => {
  it('detects a missing paragraph', () => {
    const source = ['p1', 'p2', 'p3']
    const target = ['p1', 'p3']
    const report = new ConsistencyChecker().check(source, target)
    expect(report.warnings).toHaveLength(1)
    expect(report.globalScore).toBeLessThan(100)
  })
})
```

## 19.3 Tests d’intégration

- Workflow complet sur un chapitre court.
- Mock du provider Ollama.
- Vérification que tous les steps passent.

## 19.4 Tests E2E

Scénarios :
1. Premier lancement → wizard → création projet.
2. Importer un chapitre → lancer workflow → exporter.
3. Ouvrir paramètres → changer provider → tester connexion.

## 19.5 Tests de régression

- Exécutés sur chaque PR via GitHub Actions.
- Couverture minimale 70 %.

## 19.6 Métriques de couverture

### Seuils cibles

| Scope | Couverture minimale | Blocage CI |
|---|---|---|
| Services / managers | 80 % | Oui |
| Repositories SQLite | 80 % | Oui |
| Agents | 70 % | Oui |
| IPC handlers | 60 % | Non (warning) |
| UI / composants | 50 % | Non (warning) |
| E2E parcours critiques | 100 % des 3 scénarios principaux | Oui |

### Collecte

- Vitest collecte la couverture via `c8` ou `@vitest/coverage-v8`.
- Le rapport est généré dans `coverage/` et uploadé comme artifact CI.
- `npm run test:unit -- --coverage` est exécuté localement avant chaque PR.

### Tendances

- La couverture globale ne doit pas baisser entre deux PR (assertion dans la CI).
- Les parties critiques (path traversal, validation Zod, chiffrement des clés) doivent toujours être couvertes à 100 %.
## ✅ Critères d’acceptation des tests

- - [ ] 70 % de couverture minimum.
- [ ] Les services, managers et repositories atteignent 80 % de couverture.
- [ ] Les handlers IPC sensibles (path traversal, validation Zod) sont couverts à 100 %.
- [ ] La couverture globale ne régresse pas entre deux PR.
- [ ] Les rapports de couverture sont uploadés comme artifacts CI.
- [ ] Les agents ont chacun au moins un test unitaire.
- [ ] Le workflow a un test d’intégration.
- [ ] Les parcours E2E critiques sont automatisés.
- [ ] La CI bloque les PR en cas d’échec de test.
