"""Comparaison d'un résultat obtenu par l'agent avec le résultat attendu.

Sert à l'évaluation et au contrôle des questions épinglées : mêmes valeurs,
ordre des lignes et des colonnes indifférent, colonnes en plus tolérées, même
nombre de lignes, arrondi à une décimale toléré.
"""

from datetime import date, datetime
from decimal import Decimal


def normaliser(valeur):
    if isinstance(valeur, bool) or valeur is None:
        return valeur
    if isinstance(valeur, (int, float, Decimal)):
        return float(valeur)
    if isinstance(valeur, (date, datetime)):
        return valeur.isoformat()[:10]
    if isinstance(valeur, str):
        try:
            return float(valeur)
        except ValueError:
            return valeur.strip().casefold()
    return str(valeur)


def egales(attendue, obtenue) -> bool:
    if isinstance(attendue, float) and isinstance(obtenue, float):
        # Arrondi à une décimale toléré ; un pourcentage rendu en fraction aussi.
        return any(
            abs(attendue - x) <= max(0.051, abs(attendue) * 1e-4)
            for x in (obtenue, obtenue * 100)
        )
    return attendue == obtenue


def ligne_contenue(attendue: list, obtenue: list) -> bool:
    restantes = list(obtenue)
    for valeur in attendue:
        trouvee = next((i for i, v in enumerate(restantes) if egales(valeur, v)), None)
        if trouvee is None:
            return False
        restantes.pop(trouvee)
    return True


def comparer(attendues: list[list], obtenues: list[list]) -> bool:
    if len(attendues) != len(obtenues):
        return False
    restantes = [[normaliser(v) for v in ligne] for ligne in obtenues]
    for ligne in attendues:
        ligne = [normaliser(v) for v in ligne]
        trouvee = next(
            (i for i, o in enumerate(restantes) if ligne_contenue(ligne, o)), None
        )
        if trouvee is None:
            return False
        restantes.pop(trouvee)
    return True


def reponse_correcte(attendues: list[list], requetes: list[dict]) -> bool:
    """Vrai si une des requêtes exécutées par l'agent renvoie le résultat attendu."""
    return any(comparer(attendues, r["lignes"]) for r in requetes)
