# Architecture cible

Rien de ce qui suit n'est construit. C'est la cible retenue à l'issue du cadrage ;
les points marqués « à vérifier » doivent être confirmés avant de s'y engager.

## Vue d'ensemble

```
data.gouv.nc (API OpenDataSoft)
        │  dlt (ingestion incrémentale)
        ▼
  bronze ─────────────┐
        │  dbt-trino  │   tables Apache Iceberg
  silver              │   catalogue REST : Lakekeeper (PostgreSQL)
        │  dbt-trino  │   fichiers : stockage objet S3 (rustfs)
  gold ───────────────┘
        ▲
        │  SQL
     Trino (mono-nœud) ──► Open Policy Agent : autorise chaque requête
        ▲
        │  outil « interroger » (lecture seule, vues gold, SQL validé)
     Agent LLM (OpenRouter gratuit, repli LocalAI)
        ▲
        │  question en français → réponse + SQL + graphique Plotly
     Portfolio (portfolio.tgu.ovh)
```

## Composants

| Composant | Rôle | Remarque |
|---|---|---|
| dlt | Ingestion depuis l'API de data.gouv.nc vers bronze | Chargement incrémental sur la date de modification du jeu |
| Apache Iceberg | Format de table du lac | |
| Lakekeeper | Catalogue REST Iceberg | A besoin d'un PostgreSQL : celui du namespace `datalab` existe déjà |
| rustfs | Stockage objet S3 | Déjà déployé (namespace `ia-lab`). Version stable 1.0.x (D8), sans repli MinIO. Compatible avec Iceberg et Lakekeeper : essai réel concluant le 2026-11-16 (voir plan, étape 1.1) |
| Trino | Moteur SQL, unique porte d'accès aux données | Un seul nœud suffit au volume visé |
| Open Policy Agent | Autorise chaque requête Trino | Deux rôles au moins : `public` et `analyste`, avec colonnes masquées pour `public` |
| dbt-trino | Transformations silver et gold, tests, documentation | La documentation dbt publiée tient lieu de catalogue. |
| Orchestration | Enchaîne ingestion, dbt, tests | Dagster (D9) |
| Agent | Texte-vers-SQL, lecture seule | Voir « Agent » ci-dessous |
| Interface | Chat avec graphiques | Section du portfolio, Streamlit d'abord (D5) |

## Agent

Patron repris de l'assistant professionnel datadesk, à réécrire et non à copier
(docs/decisions.md, Q1) :

- un seul outil d'interrogation, qui prend une requête SQL et, en option, la
  description d'un graphique (`chart`, `x`, `y`, `title`) ;
- la requête est **validée par du code avant exécution** (sqlglot) : lecture
  seule, schéma gold uniquement, nombre de lignes plafonné ;
- la figure Plotly est **construite côté serveur** à partir des lignes
  renvoyées ; l'interface ne fait que la dessiner ;
- la réponse affiche toujours le SQL exécuté et les jeux de données sources ;
- l'identité qui interroge Trino est celle du rôle du visiteur, jamais un
  compte d'administration : c'est OPA qui décide de ce qui est visible, pas le
  modèle.

## Maîtrise du quota LLM

Les modèles gratuits d'OpenRouter sont plafonnés (docs/environnement.md). L'agent
doit donc prévoir, dès la première version :

1. un cache des réponses par question normalisée ;
2. des questions épinglées servies uniquement depuis ce cache ;
3. une limite de questions par visiteur ;
4. un repli sur LocalAI (GPU du cluster) quand le quota est atteint.

## Évaluation

Un fichier de questions de référence versionné dans le dépôt (question, SQL
attendu ou résultat attendu). Une commande rejoue le jeu contre un modèle donné
et produit un score ; le résultat est publié dans le dépôt. La notation par
LLM-juge est une option, à condition de rester dans les quotas.

## Déploiement

Même patron que le dépôt `cv` (D10). Le chart parapluie `deploy/` (Lakekeeper
0.14.0 et Trino 1.45.0 en dépendances, namespace `lakehouse-nc`) est déployé par
l'Application ArgoCD `my-kluster/argocd/argocd-apps/lakehouse-nc-app.yaml`.

- Lakekeeper : base `lakekeeper` dans le PostgreSQL de `datalab`, migrations en
  hook ArgoCD ; un Job post-déploiement (`deploy/templates/warehouse-job.yaml`)
  amorce le catalogue et crée le warehouse `lakehouse` sur le bucket RustFS
  `lakehouse-nc`, de façon idempotente.
- Trino 484 : un seul nœud (coordinateur qui exécute aussi les tâches), tas JVM
  3 Gio, catalogue `lakehouse` (connecteur Iceberg REST vers Lakekeeper, S3
  natif vers RustFS avec ses propres clés). Pas d'ingress : accessible dans le
  cluster seulement, sans authentification jusqu'à l'étape 4 (OPA).
- Secrets : un seul SealedSecret, `my-kluster/sealed/lakehouse-nc-secrets.yaml`
  (mot de passe PostgreSQL, clé de chiffrement Lakekeeper, clés S3).

## Flux continu (optionnel, étape 5)

data.gouv.nc est une source par lots. Pour ajouter une preuve de temps réel :
un flux public continu (séismes USGS, positions AIS, vols OpenSky) ingéré par
Redpanda ou Kafka vers Iceberg, ou un CDC Debezium depuis PostgreSQL. Non
décidé (Q2).
