# Stratégie de test — MiniShop

> Modèle à compléter pendant l'Atelier 12. Une stratégie de test tient sur 2 pages : si elle est plus longue, personne ne la lit.

## 1. Périmètre et risques
| Zone | Risque métier | Probabilité | Impact | Niveau de test principal |
|---|---|---|---|---|
| Calcul des prix (`pricing.py`) | Mauvais montant facturé | Moyenne | Élevé | Unitaire + génération IA |
| API commandes | Commande perdue | Faible | Élevé | API + contrat |
| Interface | Parcours bloqué | Moyenne | Moyen | E2E + visuel |
| Performance | Abandon de panier | … | … | Charge (Locust/JMeter) |
| Sécurité | Fuite / injection | … | … | SAST, SCA, DAST (ZAP) |

## 2. Pyramide et quality gates
| Étape pipeline | Tests | Seuil bloquant |
|---|---|---|
| PR | lint, unitaires, API | 100 % OK, couverture ≥ 85 % |
| main | + E2E, visuel, sécurité | 0 vulnérabilité HIGH/CRITICAL |
| nocturne | charge, ZAP complet | p95 < 300 ms, erreurs < 1 % |

## 3. Règles pour les tests générés par IA
- **Relecture humaine obligatoire avant fusion** : tout fichier dans `tests/generated/` est relu ligne par ligne avant merge sur `main` (vérification de l'absence d'hallucinations, de la pertinence des `assert`, de la conformité à `specs/pricing.feature` et du diagnostic des `# DIVERGENCE SPEC/CODE`).
- **Marqueur `@pytest.mark.generated`** : obligatoire en tête de chaque fichier généré (`pytestmark = [pytest.mark.generated, pytest.mark.unit]`) pour tracer son origine, isoler son exécution en CI et garantir qu'aucun test généré non relu ne passe en production.
- **Validation par mutation (quality gate)** : la couverture seule ne suffit pas ; un test généré doit échouer si on casse la règle métier qu'il vérifie (`python ai_tools/mutation_score.py`, cible ≥ 85 % — score mesuré à l'Atelier 3 : **87 %** pour le LLM contre **62 %** pour le générateur déterministe `offline`).
- **Contexte source obligatoire dans le prompt** : toute génération par LLM doit inclure le code source sous test en plus de la spécification (sans code source, le taux d'échec par hallucination atteint 26/28 tests).
- **Données sensibles interdites dans les prompts** : aucun secret (clé API, token, mot de passe), donnée personnelle client (RGPD) ou code propriétaire confidentiel ne doit être transmis à un fournisseur externe ; pour tout contexte sensible, basculer sur un modèle local (`LLM_PROVIDER=ollama`) ou le moteur déterministe (`LLM_PROVIDER=offline`).
- **Responsabilité de l'auteur de la PR** : le développeur qui ouvre la Pull Request reste pleinement responsable de la validité et de la maintenance des tests générés soumis, au même titre que du code écrit manuellement.

## 4. Gestion des tests instables (flaky)
- Détection : `ai_tools/test_history.py` (score ≥ 0,6).
- Quarantaine : marqueur `flaky`, ticket ouvert, délai de correction 5 jours.

## 5. Indicateurs suivis
Taux de réussite sur main, durée de la suite, nombre de tests flaky, couverture, MTTR d'une régression.
