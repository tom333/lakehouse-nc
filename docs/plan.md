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

### Planification (2026-11-16)

Dagster partagé réactivé à la demande de Thomas (`my-kluster`, chart 1.13.30),
avec un emplacement de code `lakehouse-nc` :

- `orchestration/definitions.py` : assets dlt `bronze/<table>` puis modèles dbt
  (clés `silver/...`, `gold/...`), job `quotidien`, planifié chaque jour à 6 h
  heure de Nouméa et actif dès le déploiement (`DefaultScheduleStatus.RUNNING`).
- Image `localhost:32000/lakehouse-nc-dagster:latest` (`Dockerfile`), serveur de
  code dans le namespace `dagster` (`deploy/dagster/`, application ArgoCD
  `lakehouse-nc-dagster`). Mise à jour : `scripts/publier-code-dagster.sh`.
- Les runs reçoivent le secret `lakehouse-nc-dagster` et `TRINO_HOST` par le
  contexte de conteneur (`DAGSTER_CONTAINER_CONTEXT`).
- Premier run complet réussi dans le cluster (ingestion puis `dbt build`).
- Pièges rencontrés : l'image doit contenir `dagster-postgres` (le run écrit dans
  la base de Dagster) et `/opt/dagster/dagster_home` doit être inscriptible par
  l'utilisateur 1000.
- À surveiller : le run launcher applique à tous les runs les variables propres
  à accidents (`dagster-ducklake-config`, `rustfs-credentials-dagster`), dont
  `AWS_ENDPOINT_URL`. Sans effet aujourd'hui (dlt et pyiceberg reçoivent une
  adresse explicite) ; à déplacer dans le contexte d'accidents.

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

### Résultat de l'étape 2 (2026-11-16)

- Agent dans `agent/` (installé par le portfolio depuis GitHub ; dépendances de
  base légères, l'extra `pipeline` porte dlt, dbt et Dagster) :
  - `sql.py` : validation sqlglot (une seule instruction, lecture seule, tables
    `lakehouse.gold` seulement, fonctions de table interdites, `LIMIT 1000`),
    exécution Trino sous l'utilisateur `public` ;
  - `graphique.py` : figure Plotly construite côté serveur ;
  - `schema.py` : schéma décrit au modèle à partir des commentaires Iceberg,
    écrits par dbt (`persist_docs` sur gold) ;
  - `modeles.py` : modèles gratuits d'OpenRouter acceptant les outils, lus dans
    l'API (aucun modèle payant : la clé du compte peut payer), LocalAI en repli
    si `LOCALAI_API_KEY` est fourni ;
  - `cache.py`, `agent.py` : cache par question normalisée, quota quotidien.
- 34 tests (`uv run pytest`), dont 21 cas de validation SQL.
- Portfolio : section « Interrogez les données ouvertes de Nouvelle-Calédonie »,
  réponse + graphique + SQL et données + jeux sources, 4 questions d'exemple,
  10 questions par visite, 200 par jour. Ancien agent LangChain/DuckLake retiré.
- Vérifié dans le pod du portfolio : réponse et SQL sur une question véhicules ;
  `DROP TABLE` et lecture de bronze refusés par le code avant Trino.
- Modèle utilisé par défaut : `nvidia/nemotron-3-ultra-550b-a55b:free`
  (3 à 21 s par question pendant les essais).

Reste à faire : repli LocalAI non branché (la clé LocalAI doit être fournie au
portfolio) ; cache en mémoire (perdu au redémarrage du pod, qui s'endort avec
Sablier) ; secret OpenRouter du portfolio créé à la main, hors Sealed Secrets.

### Incident de sécurité traité pendant l'étape 2 (2026-11-16)

RustFS tournait avec les identifiants par défaut (`rustfsadmin`), exposé sur
Internet : son secret ne contenait pas `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY`.
Identifiants remplacés partout (RustFS, MLflow, Dagster accidents, lakehouse-nc),
anciens identifiants refusés, consommateurs vérifiés. Le filtre `ipAllowList`
ajouté sur `rustfs.tgu.ovh` ne protège qu'en partie : le routeur présente une
partie du trafic Internet sous l'adresse 192.168.88.1.

## Étape 3 — Questions épinglées et évaluation

### Résultat de l'étape 3 (2026-11-16)

- **Questions épinglées** (`agent/epinglees.py`, `agent/epinglees.json`) : 4
  questions dont la réponse est calculée à l'avance et livrée avec l'agent, servie
  sans appel au modèle même après un redémarrage du portfolio. Une réponse n'est
  épinglée que si une des requêtes de l'agent renvoie le résultat d'un SQL de
  référence. Ce contrôle a révélé que le modèle comptait tout le parc (1 296
  véhicules électriques) au lieu du parc en circulation (1 264) : la description
  dbt de `fct_immatriculations` précise désormais le filtre à appliquer.
- **Évaluation** (`evaluation/`) : 52 questions de référence, dont 4 à refuser
  (hors sujet ou demande de suppression). Le résultat attendu est celui d'un SQL
  exécuté au moment de l'évaluation, les données changeant chaque jour. Commande :
  `uv run python -m evaluation.evaluer --modele <modèle> [...]`.

| Modèle (gratuit, OpenRouter) | Score | Durée médiane |
|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b` | 98,1 % (51/52) | 10,4 s |
| `cohere/north-mini-code` | 90,4 % (47/52) | 3,1 s |
| `baidu/ernie-5.5-flash-preview` | 86,5 % (45/52) | 4,2 s |

- Notation stricte : une réponse qui contient la bonne valeur au milieu de lignes
  en plus est comptée fausse (seul échec de nemotron, 4 des 7 échecs d'ernie). Les
  vraies erreurs : commune écrite « Nouméa » au lieu de « NOUMEA » (cohere), pas de
  requête ou réponse à une autre question (ernie).
- Les modèles Google (`gemma-4`) et `inclusionai/ling-3.2-flash` n'ont pas pu être
  évalués : le fournisseur refusait les appels (429). Un passage avec des erreurs
  d'API n'est pas publié.
- Défauts corrigés en route : `par_teleservice` était du texte et devient un
  booléen ; consigne d'arrondi ajoutée (un `CAST` en `DECIMAL` sans échelle
  arrondit à l'entier) ; quatre questions ambiguës reformulées avant le passage
  publié.

Critère de fin tenu : la commande d'évaluation tourne de bout en bout et son
résultat est dans le dépôt (`evaluation/RESULTATS.md`, `evaluation/resultats/`).


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
