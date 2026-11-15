# Plan

Cinq étapes. Chacune se termine par quelque chose de vérifiable. Ne pas démarrer
une étape avant que la précédente tienne son critère de fin.

## Avant de coder : trancher les questions ouvertes

Q3, Q4, Q5 et Q7 sont tranchées (D7 confirmée, D9 à D11).

## Étape 1 — Lac et premier domaine

But : un jeu de data.gouv.nc ingéré, modélisé, requêtable dans Trino.

1. Vérifier que rustfs convient comme stockage S3 pour Lakekeeper et Iceberg
   (pas de repli MinIO, D8) ; aligner la version déclarée dans `my-kluster`.
2. Déployer Lakekeeper (base dans le PostgreSQL de `datalab`) et Trino mono-nœud
   sur le cluster, en GitOps.
3. Écrire la source dlt pour l'API de data.gouv.nc et charger le domaine
   retenu en bronze.
4. Initialiser le projet dbt-trino : modèles silver et gold du domaine, tests.

Domaine conseillé pour commencer : **véhicules** (`vehicules-immatricules-nc`,
472 159 lignes, et `transferts-certificats-d-immatriculation-des-vehicules-d-occasion-nc`,
105 484 lignes). Les deux jeux étaient mis à jour la veille de la création du
projet, ce qui donne un vrai cas d'ingestion incrémentale. Autres candidats dans
[environnement.md](environnement.md).

Critère de fin : `select` sur une vue gold depuis Trino renvoie des lignes ;
`dbt build` passe ; une seconde exécution de l'ingestion ne recharge que le
nouveau.

### Résultat de l'étape 1.1 (2026-11-16)

Essai reproductible dans `essais/stockage-s3/` : Lakekeeper v0.15.1 en local
(docker compose), stockage sur le RustFS du cluster (`https://rustfs.tgu.ovh`,
image 1.0.4), bucket `lakehouse-nc`, client PyIceberg.

- Création du warehouse : les contrôles de stockage de Lakekeeper passent
  (profil `s3-compat`, `path-style-access`, `sts-enabled: false`).
- Mode `client-managed` (le client a ses propres clés S3, cas de Trino) :
  création de table, deux ajouts, relecture de 4 lignes, 2 snapshots, purge.
- Mode `remote-signing` (Lakekeeper signe les requêtes S3) : même résultat.
- Après purge, le bucket est vide.
- Non testé : identifiants délivrés par STS (`vended-credentials`). Lakekeeper
  ne liste pas RustFS parmi les stockages testés pour STS ; inutile tant que
  Trino utilise ses propres clés.

Version de RustFS alignée dans `my-kluster` le 2026-11-16. Le chart lit
`image.rustfs.tag` : l'ancien `image.tag: "1.0.0-beta.3"` était ignoré, et l'image
retombait sur l'`appVersion` du chart (1.0.4). Le tag est maintenant épinglé à
`1.0.5` et suivi par un `customManager` Renovate. Les tags git du chart sortent
avant l'image Docker (1.0.6 en est un exemple), d'où l'épinglage séparé.

### Résultat de l'étape 1.2 (2026-11-16)

Déployé par ArgoCD (application `lakehouse-nc`, namespace `lakehouse-nc`) :
Lakekeeper v0.15.0 (base `lakekeeper` dans le PostgreSQL de `datalab`) et
Trino 484 mono-nœud. Le Job post-déploiement a amorcé Lakekeeper et créé le
warehouse `lakehouse`.

`scripts/test-fumee-trino.sh` passe : depuis Trino, création d'un schéma et
d'une table Iceberg, deux insertions, relecture de 3 lignes, 3 snapshots (la
création de table en produit un vide), suppression.

À reprendre plus tard :
- les clés S3 de Trino et du warehouse sont les clés admin de RustFS ; créer
  un utilisateur RustFS limité au bucket `lakehouse-nc` (étape 4) ;
- Trino n'a ni authentification ni ingress : accessible dans le cluster
  seulement, jusqu'à l'étape 4.

### Résultat de l'étape 1.3 (2026-11-16)

Source dlt `ingestion/data_gouv_nc.py`, lancée par `uv run python -m
ingestion.pipeline [table ...]` (variables d'environnement décrites en tête de
`ingestion/pipeline.py`). dlt 1.32, destination `filesystem` au format Iceberg,
catalogue REST Lakekeeper, schéma `bronze`.

| Table bronze | Jeu data.gouv.nc | Clé | Curseur (recouvrement) | Lignes |
|---|---|---|---|---|
| `vehicules_immatricules` | `vehicules-immatricules-nc` | `numero_immat` | `date_mise_a_jour` (1 jour) | 472 159 |
| `transferts_vehicules_occasion` | `transferts-certificats-d-immatriculation-des-vehicules-d-occasion-nc` | `timestamp_transaction`, `numero_immat` | `timestamp_transaction` (3 jours) | 105 484 |

- Export Parquet de l'API filtré côté serveur (`where` sur le curseur), donc typé
  à la source.
- Premier chargement d'une table en `replace` (un commit, 116 s pour les
  véhicules), puis merge `upsert` : dlt découpe l'upsert en commits de 1 000
  lignes, inutilisable pour un chargement complet (106 commits et plus de 4 min
  pour les 105 484 transferts).
- Seconde exécution : 2 lignes extraites pour les véhicules, aucune écriture
  (upsert sans changement), 4,5 s. Critère « ne recharge que le nouveau » tenu.
- L'export Parquet de data.gouv.nc tronque `timestamp_transaction` à la seconde
  (l'API JSON donne les millisecondes). La clé reste unique.
- Le warehouse annonce l'adresse publique `https://rustfs.tgu.ovh` : Lakekeeper
  la renvoie avec chaque table, et l'ingestion doit pouvoir tourner hors du
  cluster. Le Job du chart met à jour le stockage d'un warehouse existant.
- Piège ArgoCD : modifier seulement un hook (le Job) ne désynchronise pas
  l'application ; il faut lancer une synchronisation manuelle pour le rejouer.

### Résultat de l'étape 1.4 (2026-11-16)

Projet dbt-trino dans `transformation/` (dbt-core 1.12.7, dbt-trino 1.12.0).
En local : `kubectl -n lakehouse-nc port-forward svc/trino 8080:8080`, puis
`cd transformation && DBT_PROFILES_DIR=. uv run dbt build`.

- silver : `silver_vehicules`, `silver_transferts` (dates sentinelles 1901 mises
  à NULL, provinces normalisées, communes et énergies des transferts alignées
  sur celles des véhicules) ; seed `energies` (codes de la carte grise).
- gold, modèle en étoile : faits `fct_immatriculations` (un véhicule) et
  `fct_transferts` (une vente d'occasion) ; dimensions `dim_date` (depuis 1900,
  le parc compte 178 véhicules d'avant 1950), `dim_commune`, `dim_energie`,
  `dim_genre`. Colonnes décrites en français pour l'agent.
- `dbt build` : 8 modèles, 1 seed, 31 tests ; 39 succès, 1 avertissement assumé
  (6 transferts portent sur un véhicule absent du parc publié).
- Codes d'énergie `GE` et `HE` (3 véhicules) sans libellé sûr : classés
  « Inconnue » plutôt qu'inventés. Le code `/` est « Non renseignée » : il touche
  5 316 voitures particulières, ce n'est donc pas « sans moteur ».

Critères de fin de l'étape 1 tenus : `select` sur gold depuis Trino, `dbt build`
vert, seconde ingestion limitée au nouveau.

Reste à faire avant l'étape 2 : planifier ingestion puis `dbt build` sur le
cluster (Dagster, D9). L'application Dagster de `my-kluster` est désactivée et
partagée avec d'autres projets : décision à prendre avec Thomas.

## Étape 2 — Agent dans le portfolio

But : la section « Interrogez mon AI Factory » du portfolio interroge Trino et
affiche des graphiques.

1. Écrire l'outil d'interrogation : validation sqlglot, exécution Trino,
   construction de la figure Plotly.
2. Brancher l'agent sur un modèle gratuit d'OpenRouter, avec repli LocalAI.
3. Remplacer la section existante de `portfolio/main.py` (aujourd'hui
   `create_sql_agent` sur DuckLake avec `openai/gpt-4o`).
4. Cache des réponses et limite par visiteur.

Critère de fin : sur `portfolio.tgu.ovh`, une question sur les véhicules renvoie
une réponse, le SQL exécuté et un graphique ; une requête d'écriture ou hors
gold est refusée par le code, avant Trino.

## Étape 3 — Questions épinglées et évaluation

1. Quatre à six questions épinglées sur la page d'accueil, servies du cache.
2. Jeu de 50 à 100 questions de référence et commande d'évaluation.
3. Score publié dans le dépôt, pour au moins deux modèles.

Critère de fin : la commande d'évaluation tourne de bout en bout et son
résultat est dans le dépôt.

## Étape 4 — Gouvernance OPA

1. Brancher OPA sur Trino.
2. Deux rôles, `public` et `analyste` ; au moins une colonne masquée et une
   table refusée pour `public`.
3. Tests des politiques exécutés en CI.

Critère de fin : la même question posée sous les deux rôles renvoie deux
résultats différents, et l'agent explique un refus au lieu d'inventer.

## Étape 5 — Flux continu (optionnel)

Voir [architecture.md](architecture.md). À ne lancer que si Thomas confirme Q2.

## À la fin de chaque étape

- Mettre à jour l'état en tête du `README.md`.
- Noter dans [decisions.md](decisions.md) toute décision prise en route.
- Relever les chiffres utiles au CV (jeux ingérés, modèles dbt, tests, score).

## Suites côté CV

Quand la démo est en ligne : ajouter le projet aux trois fichiers du dépôt `cv`
(`src/data/CV.md`, `static/index.html`, `chat_bot/data/CV.md`), puis relancer
l'ingestion du chatbot du CV.
