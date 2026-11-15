# Environnement

Faits relevés le 2026-11-16. Tout ce qui touche au cluster peut avoir changé :
revérifier avant de s'appuyer dessus.

## Cluster personnel

Dépôt GitOps : `/data/projets/perso/my-kluster` (public, `github.com/tom333/my-kluster`).
**Lire son `CLAUDE.md` avant toute modification** : il fixe les conventions.

- MicroK8s, deux nœuds : `pc` (12 CPU, 64 Gio, 1 GPU, environ 48 % de mémoire
  utilisée) et `jeux` (8 CPU, 16 Gio, 1 GPU).
- ArgoCD, patron « App of Apps » : tout fichier `*.yaml` de
  `argocd/argocd-apps/` devient une application ; le suffixe `.disable`
  désactive. On renomme, on ne supprime jamais.
- Domaine `*.tgu.ovh`, Traefik, cert-manager avec Let's Encrypt.
- Secrets : Sealed Secrets uniquement, dans `sealed/`. Un `kind: Secret` en
  clair est interdit et bloqué par gitleaks.
- Registre d'images local : `localhost:32000`.
- Contexte kubectl : `microk8s`.

Services déjà présents et utiles ici :

| Service | Namespace | Usage pour ce projet |
|---|---|---|
| PostgreSQL (Bitnami) | `datalab` | Base du catalogue Lakekeeper |
| rustfs (S3) | `ia-lab` | Stockage des fichiers Iceberg. Image `rustfs/rustfs:1.0.5`, épinglée dans `my-kluster/argocd/argocd-apps/rustfs-app.yaml` (`image.rustfs.tag`) et suivie par Renovate. Compatibilité avec Iceberg et Lakekeeper vérifiée le 2026-11-16 |
| LocalAI (GPU) | `localai` | Repli LLM ; accès limité au réseau local, jeton d'API |
| MLflow | `ia-lab` | Non requis |
| Dagster | `dagster` | Application désactivée (`dagster.yaml.disable`) |
| Qdrant | `datalab` | Non requis |

## Dépôts voisins

| Dépôt | Chemin | Lien avec ce projet |
|---|---|---|
| portfolio | `/data/projets/perso/portfolio` | Héberge la démo. Streamlit, un seul `main.py`, en ligne sur `portfolio.tgu.ovh` |
| cv | `/data/projets/perso/cv` | CV à mettre à jour quand la démo est en ligne |
| my-kluster | `/data/projets/perso/my-kluster` | Déploiement |
| accidents, poissons, essence-nc | `/data/projets/perso/` | Projets ML existants, avec leur propre lac DuckLake |
| datadesk | `/data/projets/dinum/datadesk` | Référence du patron « graphique dans le chat ». Dépôt professionnel : lecture seule, ne rien copier (decisions.md, Q1) |

### État du portfolio à connaître

- Section texte-vers-SQL existante : `create_sql_agent` (LangChain) sur un
  DuckLake, modèle `openai/gpt-4o` via OpenRouter. C'est elle que l'étape 2 remplace.
- Le dépôt n'a **pas de remote Git** et presque tous ses fichiers sont non suivis.
- Le `Dockerfile` injecte une balise `og:image` vers une image qui n'existe pas.
- Le pod avait redémarré 12 fois en 70 jours.

## Comptes Git

Tout dépôt sous `/data/projets/perso/` utilise le compte personnel (`tom333`).
Les dépôts sous `/data/projets/dinum/` sont professionnels : ne pas y écrire
dans le cadre de ce projet.

## data.gouv.nc

Portail OpenDataSoft. API Explore v2.1, sans authentification :

```
https://data.gouv.nc/api/explore/v2.1/catalog/datasets
https://data.gouv.nc/api/explore/v2.1/catalog/datasets/<dataset_id>/records
https://data.gouv.nc/api/explore/v2.1/catalog/datasets/<dataset_id>/exports/parquet
```

Vérifié : le catalogue répond et compte **375 jeux de données**. Les formats
d'export disponibles (dont Parquet) sont à confirmer jeu par jeu.

Jeux les plus volumineux, avec leur dernière modification :

| Identifiant | Lignes | Modifié | Producteur |
|---|---|---|---|
| `vehicules-immatricules-nc` | 472 159 | 2026-11-15 | Gouvernement |
| `recensement-de-la-population-2019-individus-nc` | 271 407 | 2026-08-05 | ISEE |
| `demandeurs_emploi` | 264 648 | 2024-04-23 | Gouvernement |
| `actions_sessions_inscriptions_formations_ifap` | 199 527 | 2026-11-09 | IFAP |
| `peche_psud` | 137 695 | 2024-04-29 | Province Sud |
| `rp-2019-logements` | 109 025 | 2026-08-05 | ISEE |
| `transferts-certificats-d-immatriculation-des-vehicules-d-occasion-nc` | 105 484 | 2026-11-15 | Gouvernement |
| `releve_prix_produits_mer_marche_moselle` | 78 954 | 2026-08-05 | Gouvernement |
| `parcelles-cadastrales-nc` | 77 097 | 2026-11-15 | Gouvernement |
| `sempex_prix_medicaments_en_vigueur` | 62 754 | 2026-11-11 | Gouvernement |
| `adresses_nouvelle_caledonie` | 52 073 | 2026-11-13 | GIE SERAIL |

Le référentiel des entreprises (RIDET) n'a pas été recherché dans le catalogue.

Le recensement est diffusé au niveau individuel : bon candidat pour montrer le
masquage de colonnes par OPA à l'étape 4.

## Modèles gratuits d'OpenRouter

D'après des sources secondaires consultées le 2026-11-16, **à confirmer dans la
documentation officielle** :

- 20 requêtes par minute sur les modèles `:free` ;
- 50 requêtes par jour, ou 1 000 par jour si le compte a acheté au moins 10 $
  de crédits une fois ;
- le compteur du jour se lit par `GET https://openrouter.ai/api/v1/key` ;
- la liste des modèles gratuits change souvent : ne pas coder un identifiant en dur.

Le cluster détient déjà une clé OpenRouter dans le secret `openrouter-api-key`
du namespace `cv`. Pour ce projet, créer un secret scellé propre au namespace
du projet plutôt que de réutiliser celui-là.

## Sources consultées pendant le cadrage

- https://docs.evidence.dev/core-concepts/data-sources/trino
- https://openrouter.ai/blog/tutorials/free-llm-apis-compared/
- https://www.truefoundry.com/fr/blog/openrouter-rate-limits-your-free-tier-depends-on-what-youve-already-paid
- https://github.com/assistant-ui/assistant-ui
