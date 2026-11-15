# CLAUDE.md

Consignes pour un agent de code qui reprend ce projet.

## État

Projet initié le 2026-11-16. **Aucun déploiement.** Le dépôt contient la
documentation et un essai jetable (`essais/stockage-s3/`) qui a validé Iceberg
sur RustFS via Lakekeeper. Aucun commit n'a été fait et le dépôt n'a pas de remote.

## À lire avant d'agir

1. `docs/cadrage.md` — pourquoi le projet existe et ce qu'il doit prouver.
2. `docs/decisions.md` — décisions prises (D1 à D11) et questions ouvertes (Q1, Q2, Q6).
3. `docs/plan.md` — étapes et critères de fin.
4. `docs/architecture.md` et `docs/environnement.md` — cible technique et existant.
5. `/data/projets/perso/my-kluster/CLAUDE.md` — avant de toucher au cluster.

## Première action d'une nouvelle session

Q3 à Q5 sont tranchées (D9 à D11). Le stockage RustFS est validé (plan, étape
1.1). Suite : étape 1.2 (Lakekeeper et Trino en GitOps).

## Règles

- **Ne pas rouvrir les décisions D1 à D11** sans demande de Thomas : pas
  d'OpenMetadata, pas d'outil de BI, données data.gouv.nc, modèles gratuits
  d'OpenRouter, démo dans le portfolio.
- **Ne rien copier depuis `/data/projets/dinum/`** : ce sont des dépôts
  professionnels. datadesk sert de référence de conception, à lire seulement.
- **Compte Git personnel** (`tom333`) pour ce dépôt et pour `portfolio`, `cv`,
  `my-kluster`.
- **Aucun secret en clair** : Sealed Secrets dans `my-kluster/sealed/`. Ce
  dépôt est destiné à devenir public.
- **L'agent ne fait jamais confiance au modèle pour la sécurité** : la requête
  SQL est validée par du code (lecture seule, schéma gold, lignes plafonnées),
  et c'est OPA qui décide de ce qui est visible.
- **Points marqués « à vérifier »** dans la documentation : les confirmer
  (documentation à jour de la bibliothèque, essai réel) avant de construire dessus.
- **Ne pas survendre** : les volumes sont petits (au plus 472 159 lignes). Le
  projet prouve l'architecture et l'agent, pas la tenue en charge.
- Français pour la documentation, les messages de commit et l'interface.
- Python géré avec `uv`, formatage par `ruff`.

## Tenir la documentation à jour

À la fin de chaque étape : état en tête du `README.md`, décisions nouvelles dans
`docs/decisions.md`, chiffres utiles au CV relevés (jeux ingérés, modèles dbt,
tests, score d'évaluation).
