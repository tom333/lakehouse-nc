# lakehouse-nc

Lakehouse ouvert de la Nouvelle-Calédonie : les données de [data.gouv.nc](https://data.gouv.nc)
dans un lac Apache Iceberg, interrogeables en langage naturel par un agent qui
répond avec le SQL exécuté et un graphique, sous le contrôle d'Open Policy Agent.

Version légère et publique de l'architecture « datastack » : mêmes principes
(Trino comme unique porte d'accès, autorisation par OPA, architecture Medallion,
agent sur données gouvernées), sans catalogue OpenMetadata ni outil de BI.

**État (2026-11-16) : étapes 1 et 2 terminées.** L'agent répond sur
[portfolio.tgu.ovh](https://portfolio.tgu.ovh). Lakekeeper et Trino sont déployés en
GitOps sur le cluster ; Trino lit et écrit des tables Iceberg stockées sur RustFS
(`scripts/test-fumee-trino.sh`). Deux jeux de data.gouv.nc (véhicules immatriculés, transferts de véhicules
d'occasion : 577 643 lignes) sont chargés en bronze par dlt, en incrémental, puis
modélisés par dbt en silver et en gold (modèle en étoile : 8 modèles, 31 tests).
Le tout tourne chaque jour à 6 h (heure de Nouméa), orchestré par Dagster.

## Par où commencer

| Document | Contenu |
|---|---|
| [docs/cadrage.md](docs/cadrage.md) | Pourquoi ce projet, objectifs, hors périmètre, critères de réussite |
| [docs/architecture.md](docs/architecture.md) | Composants, flux, choix techniques |
| [docs/plan.md](docs/plan.md) | Étapes, critères de fin, première tâche |
| [docs/decisions.md](docs/decisions.md) | Décisions prises et questions ouvertes |
| [docs/environnement.md](docs/environnement.md) | Cluster, dépôts voisins, API data.gouv.nc, quotas LLM |
| [CLAUDE.md](CLAUDE.md) | Consignes pour un agent de code qui reprend le projet |

## Stack cible

dlt → Apache Iceberg (Lakekeeper, stockage S3) → Trino + Open Policy Agent → dbt →
agent texte-vers-SQL avec graphiques Plotly dans la conversation, exposé dans le
portfolio (`portfolio.tgu.ovh`).
