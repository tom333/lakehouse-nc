"""Agent texte-vers-SQL : une question en français, une réponse avec le SQL
exécuté, les jeux sources et éventuellement un graphique.

Le modèle n'a qu'un outil, `interroger`. Le code valide chaque requête avant
Trino (agent.sql) et construit lui-même la figure (agent.graphique).
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import sqlglot
from openai import APIError
from sqlglot import exp
from trino.exceptions import TrinoQueryError

from agent import graphique, schema, sql
from agent.modeles import Modele, candidats

logger = logging.getLogger(__name__)

TOURS_MAX = 5
TEXTE_ECHEC = "Je n'ai pas réussi à aboutir à une réponse fiable en quelques essais."
LIGNES_POUR_LE_MODELE = 30

# Jeu data.gouv.nc à l'origine de chaque table de faits.
SOURCES = {
    "fct_immatriculations": "vehicules-immatricules-nc",
    "fct_transferts": "transferts-certificats-d-immatriculation-des-vehicules-d-occasion-nc",
}

OUTIL = {
    "type": "function",
    "function": {
        "name": "interroger",
        "description": (
            "Exécute une requête SQL Trino en lecture seule sur les tables du schéma gold "
            "et renvoie les colonnes et les premières lignes. Peut aussi produire un graphique."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "Une seule requête SELECT."},
                "graphique": {
                    "type": "object",
                    "description": "Facultatif : graphique à tracer à partir du résultat.",
                    "properties": {
                        "type": {"type": "string", "enum": list(graphique.TYPES)},
                        "x": {
                            "type": "string",
                            "description": "Colonne en abscisse ou étiquettes.",
                        },
                        "y": {"type": "string", "description": "Colonne des valeurs."},
                        "titre": {"type": "string"},
                    },
                    "required": ["type", "x", "y"],
                },
            },
            "required": ["sql"],
        },
    },
}

CONSIGNES = """Tu es l'assistant de données du lakehouse ouvert de la Nouvelle-Calédonie.
Tu réponds en français aux questions sur les véhicules immatriculés et les ventes de
véhicules d'occasion, à partir des données ouvertes de data.gouv.nc.

Règles :
- Pour obtenir des chiffres, appelle l'outil `interroger` avec une requête SQL Trino.
  N'invente jamais un chiffre : chaque nombre de ta réponse vient d'un résultat de requête.
- N'utilise que les tables et colonnes décrites ci-dessous (schéma gold).
- Si la requête échoue, lis l'erreur, corrige la requête et réessaie.
- Pour une moyenne ou un pourcentage arrondi, écris round(avg(x), 1) : un CAST en
  DECIMAL sans échelle arrondit à l'entier.
- Si la question sort de ces données, dis-le simplement, sans requête.
- Demande un graphique quand il aide à lire le résultat (évolution, comparaison).
- Réponse finale courte : la réponse, les chiffres clés, et les limites éventuelles des
  données (par exemple : les transferts commencent en janvier 2022).

Schéma gold :
{schema}
"""


@dataclass
class Reponse:
    texte: str
    sql: str | None = None
    colonnes: list[str] = field(default_factory=list)
    lignes: list[list] = field(default_factory=list)
    figure: str | None = None  # Figure Plotly sérialisée en JSON
    sources: list[str] = field(default_factory=list)
    modele: str | None = None
    calculee_le: str | None = None  # renseigné pour les questions épinglées
    # Toutes les requêtes exécutées pendant la conversation (sql, colonnes, lignes)
    requetes: list[dict] = field(default_factory=list)

    def en_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def consignes() -> str:
    return CONSIGNES.format(schema=schema.decrire())


def sources_de(requete: str) -> list[str]:
    tables = {
        t.name for t in sqlglot.parse_one(requete, read="trino").find_all(exp.Table)
    }
    return sorted(SOURCES[t] for t in tables if t in SOURCES)


def _appel_outil(arguments: str, reponse: Reponse) -> str:
    """Exécute un appel de l'outil ; renvoie le message destiné au modèle."""
    try:
        args = json.loads(arguments)
        resultat = sql.executer(args["sql"])
    except (json.JSONDecodeError, KeyError):
        return "Erreur : arguments invalides, il faut au moins le champ « sql »."
    except sql.RequeteRefusee as e:
        return f"Requête refusée : {e}"
    except TrinoQueryError as e:
        return f"Erreur Trino : {e.message}"

    reponse.sql = resultat.sql
    reponse.colonnes = resultat.colonnes
    reponse.lignes = [list(ligne) for ligne in resultat.lignes]
    reponse.sources = sources_de(resultat.sql)
    reponse.requetes.append(
        {"sql": resultat.sql, "colonnes": resultat.colonnes, "lignes": reponse.lignes}
    )
    reponse.figure = None
    message = {
        "colonnes": resultat.colonnes,
        "lignes": reponse.lignes[:LIGNES_POUR_LE_MODELE],
        "nombre_de_lignes": len(resultat.lignes),
    }
    if description := args.get("graphique"):
        try:
            reponse.figure = graphique.construire(resultat, description).to_json()
            message["graphique"] = "affiché"
        except graphique.GraphiqueRefuse as e:
            message["graphique"] = f"refusé : {e}"
    return json.dumps(message, default=str, ensure_ascii=False)


def _converser(modele: Modele, question: str) -> Reponse:
    reponse = Reponse(texte="", modele=modele.nom)
    messages = [
        {"role": "system", "content": consignes()},
        {"role": "user", "content": question},
    ]
    for _ in range(TOURS_MAX):
        choix = modele.client.chat.completions.create(
            model=modele.nom, messages=messages, tools=[OUTIL], temperature=0
        ).choices[0]
        message = choix.message
        if not message.tool_calls:
            reponse.texte = (message.content or "").strip()
            return reponse
        messages.append(message.model_dump(exclude_none=True))
        for appel in message.tool_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": appel.id,
                    "content": _appel_outil(appel.function.arguments, reponse),
                }
            )
    reponse.texte = TEXTE_ECHEC
    return reponse


def repondre(question: str, modeles: list[Modele] | None = None) -> Reponse:
    """Essaie chaque modèle (par défaut les candidats) ; passe au suivant si l'API échoue."""
    for modele in candidats() if modeles is None else modeles:
        try:
            return _converser(modele, question)
        except APIError as e:
            logger.warning("Modèle %s indisponible : %s", modele.nom, e)
    return Reponse(texte="Aucun modèle de langage n'est disponible pour le moment.")


def repondre_avec_cache(
    question: str, cache, questions_par_jour: int
) -> tuple[Reponse, bool]:
    """Sert la question depuis le cache, sinon interroge un modèle dans la limite du
    quota quotidien. Renvoie la réponse et True si elle vient du cache."""
    if connue := cache.lire(question):
        return Reponse(**connue), True
    if not cache.consommer(questions_par_jour):
        return Reponse(
            texte="Le quota quotidien de questions est atteint. Revenez demain, ou essayez "
            "une des questions proposées."
        ), False
    reponse = repondre(question)
    if reponse.sql:  # seules les réponses appuyées sur une requête sont gardées
        cache.ecrire(question, reponse.en_dict())
    return reponse, False
