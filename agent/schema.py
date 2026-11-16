"""Description du schéma gold pour le modèle, lue dans Trino.

Les descriptions viennent des commentaires écrits par dbt (persist_docs) : la
documentation des modèles est la seule source, sans copie dans l'agent.
"""

from collections import defaultdict

from agent.sql import CATALOGUE, SCHEMA, connexion


def decrire() -> str:
    with connexion() as conn:
        curseur = conn.cursor()
        curseur.execute(
            "SELECT table_name, comment FROM system.metadata.table_comments "
            "WHERE catalog_name = ? AND schema_name = ?",
            (CATALOGUE, SCHEMA),
        )
        tables = {
            nom: (commentaire or "").strip() for nom, commentaire in curseur.fetchall()
        }
        curseur.execute(
            "SELECT table_name, column_name, type_name, remarks FROM system.jdbc.columns "
            "WHERE table_cat = ? AND table_schem = ? ORDER BY table_name, ordinal_position",
            (CATALOGUE, SCHEMA),
        )
        colonnes = defaultdict(list)
        for table, colonne, type_, remarque in curseur.fetchall():
            colonnes[table].append((colonne, type_, (remarque or "").strip()))

    blocs = []
    for table in sorted(tables):
        lignes = [f"Table {SCHEMA}.{table} : {tables[table]}"]
        for colonne, type_, remarque in colonnes[table]:
            lignes.append(
                f"  - {colonne} ({type_})" + (f" : {remarque}" if remarque else "")
            )
        blocs.append("\n".join(lignes))
    return "\n\n".join(blocs)
