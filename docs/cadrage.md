# Cadrage

## Pourquoi ce projet

Le projet est né d'une relecture du CV de Thomas par un regard de recruteur data
(session du 15-16 novembre 2026, dépôt `/data/projets/perso/cv`). Le CV prouve la
capacité à construire des plateformes, mais plusieurs preuves manquent, et la
plupart ne peuvent pas venir des projets professionnels :

- le projet phare, la plateforme datastack du gouvernement, est en qualification
  et sa mise en production dépend d'autres services ;
- aucune démonstration publique et cliquable de la combinaison qui distingue le
  profil : lakehouse + gouvernance + agent IA sur données gouvernées ;
- dbt et la modélisation dimensionnelle sont cités en compétence, dans aucun projet ;
- pas de temps réel ni de CDC ;
- pas de validation extérieure (tout est chez le même employeur) ;
- pas de chiffre d'usage ou de qualité que Thomas maîtrise seul.

Les projets personnels existants (accidents, prix des poissons, énergie) sont
tous du machine learning par lots : un projet de plus du même type n'apporterait
rien.

## Objectif

Une démonstration publique, en ligne, où un visiteur pose une question en
français sur les données ouvertes de la Nouvelle-Calédonie et obtient une
réponse avec le SQL exécuté, les sources et un graphique. Derrière : un lac
Iceberg, Trino, OPA et des modèles dbt, déployés en GitOps sur le cluster
personnel.

## Ce que le projet doit prouver

| Preuve attendue | Comment |
|---|---|
| Architecture lakehouse gouvernée | Iceberg + Trino, chaque requête autorisée par OPA |
| Modélisation | Modèle dimensionnel dbt (bronze / silver / gold), tests, documentation publiée |
| Agent sur données gouvernées | Texte-vers-SQL limité aux vues gold, SQL validé avant exécution |
| Qualité mesurée | Jeu de 50 à 100 questions de référence, score publié, comparaison de modèles |
| Usage réel | Fréquentation mesurée (Umami est déjà en place sur le portfolio) |
| Maîtrise des coûts | Modèles gratuits, cache, quotas, repli sur un LLM local |

## Contraintes fixées par Thomas

- Version **légère** : pas d'OpenMetadata.
- Données : **data.gouv.nc**.
- LLM : **modèles gratuits d'OpenRouter**.
- Pas d'outil de BI : **les graphiques s'affichent dans la conversation**.
- La démo peut vivre **dans le projet portfolio** (`/data/projets/perso/portfolio`).

## Hors périmètre

- OpenMetadata, Superset, Evidence ou tout autre outil de BI.
- Portail d'habilitation (PassLagon) et demandes d'accès.
- Authentification des visiteurs : la démo est publique et anonyme.
- Écriture dans le lac par l'agent : lecture seule.
- Reprise de code des dépôts professionnels (voir docs/decisions.md, Q1).

## Limite assumée

Les jeux de data.gouv.nc sont petits : le plus gros compte 472 159 lignes
(véhicules immatriculés), le catalogue 375 jeux. Ce projet ne prouvera pas la
tenue en volume. Il prouve l'architecture, la gouvernance, la modélisation et
l'agent. Ne pas écrire le contraire dans le CV.

## Critères de réussite

1. Une URL publique où une question en français renvoie une réponse correcte
   avec SQL et graphique.
2. Quatre à six questions épinglées, cliquables, servies depuis un cache.
3. Un score d'évaluation publié dans le dépôt, reproductible par une commande.
4. Un dépôt GitHub public, lisible par un recruteur technique en dix minutes.
5. Des lignes chiffrées à reporter dans le CV : nombre de jeux ingérés, de
   modèles dbt, de tests, score de l'agent, visiteurs par mois.
