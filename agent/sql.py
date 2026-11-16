"""Validation et exécution des requêtes SQL proposées par le modèle.

Le modèle n'est jamais cru sur parole : une requête n'atteint Trino que si le
code a vérifié qu'elle est une seule lecture, limitée aux tables du schéma gold,
et plafonnée en nombre de lignes.
"""

import os
from dataclasses import dataclass

import sqlglot
import trino
from sqlglot import exp

CATALOGUE = "lakehouse"
SCHEMA = "gold"
LIGNES_MAX = 1000

# Nœuds qui écrivent, administrent ou contournent le parseur.
INTERDITS = (exp.DDL, exp.DML, exp.Command, exp.Into, exp.Set, exp.Use, exp.Describe)


class RequeteRefusee(ValueError):
    """La requête ne respecte pas les règles ; le message est destiné au modèle."""


def valider(sql: str, lignes_max: int = LIGNES_MAX) -> str:
    """Renvoie la requête normalisée et plafonnée, ou lève RequeteRefusee."""
    try:
        instructions = [i for i in sqlglot.parse(sql, read="trino") if i is not None]
    except sqlglot.errors.ParseError as e:
        raise RequeteRefusee(f"SQL illisible : {e}") from e
    if len(instructions) != 1:
        raise RequeteRefusee("Une seule instruction SELECT est autorisée.")
    requete = instructions[0]
    if not isinstance(requete, exp.Query):
        raise RequeteRefusee("Seules les lectures (SELECT) sont autorisées.")
    if interdit := next(requete.find_all(*INTERDITS), None):
        raise RequeteRefusee(f"Instruction interdite : {interdit.key.upper()}.")

    ctes = {cte.alias_or_name for cte in requete.find_all(exp.CTE)}
    for table in requete.find_all(exp.Table):
        if not isinstance(table.this, exp.Identifier):
            raise RequeteRefusee("Les fonctions de table sont interdites.")
        if not table.db and table.name in ctes:
            continue
        if table.db not in ("", SCHEMA) or table.catalog not in ("", CATALOGUE):
            raise RequeteRefusee(
                f"Table {table.sql('trino')} hors du schéma {SCHEMA} : seules les "
                f"tables {CATALOGUE}.{SCHEMA} sont interrogeables."
            )

    limite = requete.args.get("limit")
    valeur = limite.expression if limite else None
    if not (
        isinstance(valeur, exp.Literal)
        and valeur.is_int
        and int(valeur.this) <= lignes_max
    ):
        requete = requete.limit(lignes_max)
    return requete.sql(dialect="trino")


@dataclass
class Resultat:
    sql: str
    colonnes: list[str]
    lignes: list[tuple]


def connexion() -> trino.dbapi.Connection:
    return trino.dbapi.connect(
        host=os.environ.get("TRINO_HOST", "trino.lakehouse-nc.svc.cluster.local"),
        port=int(os.environ.get("TRINO_PORT", "8080")),
        # Identité du visiteur : c'est OPA (étape 4) qui décidera de ce qu'elle voit.
        user=os.environ.get("TRINO_USER", "public"),
        catalog=CATALOGUE,
        schema=SCHEMA,
        session_properties={"query_max_execution_time": "30s"},
        request_timeout=40,
    )


def executer(sql: str) -> Resultat:
    """Valide puis exécute la requête sur Trino."""
    sure = valider(sql)
    with connexion() as conn:
        curseur = conn.cursor()
        curseur.execute(sure)
        lignes = curseur.fetchall()
        colonnes = [c[0] for c in curseur.description]
    return Resultat(sql=sure, colonnes=colonnes, lignes=[tuple(l) for l in lignes])
