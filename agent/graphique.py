"""Construction de la figure Plotly à partir des lignes renvoyées par Trino.

Le modèle ne fournit qu'une description (type, colonnes, titre) ; la figure est
construite ici, et la description est rejetée si elle ne correspond pas aux
colonnes du résultat.
"""

import plotly.graph_objects as go

from agent.sql import Resultat

TYPES = ("barres", "lignes", "camembert", "nuage")


class GraphiqueRefuse(ValueError):
    """La description du graphique est invalide ; le message est pour le modèle."""


def construire(resultat: Resultat, description: dict) -> go.Figure:
    type_ = description.get("type")
    x, y = description.get("x"), description.get("y")
    if type_ not in TYPES:
        raise GraphiqueRefuse(
            f"Type de graphique inconnu : {type_}. Types : {', '.join(TYPES)}."
        )
    for colonne in (x, y):
        if colonne not in resultat.colonnes:
            raise GraphiqueRefuse(
                f"Colonne {colonne!r} absente du résultat ({', '.join(resultat.colonnes)})."
            )
    xs = [ligne[resultat.colonnes.index(x)] for ligne in resultat.lignes]
    ys = [ligne[resultat.colonnes.index(y)] for ligne in resultat.lignes]

    if type_ == "barres":
        trace = go.Bar(x=xs, y=ys)
    elif type_ == "lignes":
        trace = go.Scatter(x=xs, y=ys, mode="lines+markers")
    elif type_ == "camembert":
        trace = go.Pie(labels=xs, values=ys)
    else:
        trace = go.Scatter(x=xs, y=ys, mode="markers")

    figure = go.Figure(trace)
    figure.update_layout(
        title=description.get("titre") or "",
        xaxis_title=x,
        yaxis_title=y,
        template="plotly_white",
        margin={"t": 60, "l": 40, "r": 20, "b": 40},
    )
    return figure
