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
