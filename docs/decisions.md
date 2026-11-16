# Décisions et questions ouvertes

## Décisions prises

| N° | Décision | Origine | Raison |
|---|---|---|---|
| D1 | Version légère, **sans OpenMetadata** | Thomas, 2026-11-16 | Le catalogue est tenu par la documentation dbt publiée |
| D2 | Données issues de **data.gouv.nc** | Thomas, 2026-11-16 | Données ouvertes locales, sans contrainte de confidentialité |
| D3 | **Modèles gratuits d'OpenRouter** | Thomas, 2026-11-16 | Démo publique sans coût récurrent ; impose cache, quotas et repli LocalAI |
| D4 | **Pas d'outil de BI** : graphiques dans la conversation | Thomas, 2026-11-16 | L'assistant professionnel datadesk le fait déjà (Plotly construit côté serveur) ; une brique de moins |
| D5 | Démo hébergée **dans le portfolio**, en Streamlit d'abord | Thomas pour l'emplacement ; Streamlit proposé par l'assistant | Le portfolio a déjà une section texte-vers-SQL à remplacer ; Streamlit évite un build React pour la première version |
| D6 | **Iceberg + Trino + OPA** conservés malgré la version légère | Proposé par l'assistant, non contesté | C'est la combinaison qui distingue le profil ; un seul nœud Trino suffit |
| D7 | **dbt-trino** pour silver et gold, confirmé face à Ibis le 2026-11-16 | Proposé par l'assistant, non contesté | Comble l'absence de dbt et de modélisation dans les projets du CV |
| D8 | **RustFS seul stockage S3**, sans repli MinIO | Thomas, 2026-11-16 | MinIO est déprécié ; RustFS est sorti de bêta (1.0.5). Compatibilité confirmée par essai réel le 2026-11-16 (`essais/stockage-s3/`) |
| D9 | Orchestration par **Dagster** | Thomas, 2026-11-16 (Q3) | Maîtrisé, cohérent avec le CV ; l'application ArgoCD `dagster.yaml.disable` est à réactiver |
| D10 | **Manifestes Kubernetes dans ce dépôt**, Application ArgoCD dans `my-kluster` | Thomas, 2026-11-16 (Q4) | Même patron que le dépôt `cv` |
| D11 | Nom **`lakehouse-nc`**, dépôt public sur le compte **`tom333`** | Thomas, 2026-11-16 (Q5) | Sert de preuve publique |
| D12 | Le warehouse annonce l'**adresse S3 publique** `https://rustfs.tgu.ovh` | Assistant, 2026-11-16 | Lakekeeper la renvoie avec chaque table ; l'adresse interne du cluster empêchait toute ingestion hors du cluster |
| D13 | Bronze chargé par **dlt (destination `filesystem`, format Iceberg, catalogue REST)** ; premier chargement en `replace`, puis merge `upsert` | Assistant, 2026-11-16 | dlt découpe l'upsert en commits de 1 000 lignes : inutilisable pour un chargement complet, adapté aux incréments quotidiens |
| D14 | Gold en **modèle en étoile** (`fct_immatriculations`, `fct_transferts`, dimensions date, commune, énergie, genre) | Assistant, 2026-11-16 | Comble le manque « modélisation dimensionnelle » du CV ; colonnes décrites en français pour l'agent |
| D15 | **L'agent vit dans ce dépôt** (`agent/`) et le portfolio l'installe depuis GitHub | Assistant, 2026-11-16 | Le même code sert la démo et l'évaluation (étape 3) ; le portfolio ne garde que l'interface |
| D16 | **Documentation dbt écrite dans Iceberg** (`persist_docs`), lue par l'agent dans Trino | Assistant, 2026-11-16 | Une seule source pour la description du schéma, sans copie dans l'agent |

## Options écartées

- **Superset** : jugé trop lourd par Thomas, qui voulait une alternative plus
  légère et orientée code.
- **Evidence** (SQL + Markdown compilés en site statique) : retenu un temps,
  puis abandonné au profit de D4. À savoir si la question revient : les
  requêtes tournent à la compilation, et son connecteur Trino ne gère que
  l'authentification par mot de passe.
- **Rill, Lightdash, Observable Framework** : écartés avec Evidence.
- **MinIO** : écarté comme repli de stockage, projet déprécié (D8).

## Questions ouvertes

**Q1 — Réutiliser le code de datadesk ?**
datadesk (`/data/projets/dinum/datadesk`) est un dépôt professionnel sans
fichier de licence. Par défaut : ne rien copier, réécrire le patron. Si Thomas
confirme qu'il est publié sous licence libre, en dépendre proprement.

**Q2 — Ajouter un flux continu (étape 5) ?**
Sans lui, le projet ne comble pas l'absence de temps réel et de CDC du CV.
Proposition : livrer les étapes 1 à 4, puis décider.

Q3, Q4 et Q5 sont tranchées (D9, D10, D11).

**Q6 — Interface : passer au widget assistant-ui + AG-UI ?**
Après la version Streamlit, le même patron que datadesk (widget React, serveur
AG-UI) montrerait davantage. Dépend de Q1.

Q7 (dbt ou Ibis) tranchée le 2026-11-16 : dbt, D7 confirmée. Ibis écarté pour les
transformations : il ne fournit ni tests de données, ni documentation, ni lignage,
et ne comblerait pas le manque de dbt du CV.
