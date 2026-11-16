"""Questions épinglées : réponses calculées à l'avance et livrées avec le package.

Elles sont servies sans appel au modèle, même après un redémarrage du portfolio.
Chaque réponse est contrôlée avant d'être épinglée : une des requêtes de l'agent
doit renvoyer le résultat du SQL de référence.
Recalcul : uv run python -m agent.epinglees (Trino et OPENROUTER_API_KEY requis).
"""

import json
import sys
from datetime import date
from pathlib import Path

from agent.agent import TEXTE_ECHEC, repondre
from agent.cache import Cache
from agent.comparaison import reponse_correcte
from agent.sql import executer

FICHIER = Path(__file__).with_name("epinglees.json")
ESSAIS = 3
CIRCULATION = "f.statut = 'En circulation'"
QUESTIONS = {
    "Combien de véhicules électriques sont en circulation ?": (
        "SELECT count(*) FROM fct_immatriculations f "
        "JOIN dim_energie e ON e.code_energie = f.code_energie "
        f"WHERE {CIRCULATION} AND e.famille_energie = 'Électrique'"
    ),
    "Comment évoluent les ventes de véhicules d'occasion par année ?": (
        "SELECT year(date_transaction), count(*) FROM fct_transferts GROUP BY 1"
    ),
    "Quelles sont les 10 marques les plus présentes dans le parc en circulation ?": (
        "SELECT marque, count(*) n FROM fct_immatriculations f "
        f"WHERE {CIRCULATION} GROUP BY 1 ORDER BY n DESC LIMIT 10"
    ),
    (
        "Quel pourcentage des voitures particulières en circulation est hybride ou "
        "électrique, dans chaque province ?"
    ): (
        "SELECT c.province, round(100.0 * count_if(e.famille_energie IN "
        "('Hybride', 'Hybride rechargeable', 'Électrique')) / count(*), 1) "
        "FROM fct_immatriculations f "
        "JOIN dim_energie e ON e.code_energie = f.code_energie "
        "JOIN dim_commune c ON c.commune = f.commune "
        f"WHERE {CIRCULATION} AND f.code_genre = 'VP' GROUP BY 1"
    ),
}


def charger(cache: Cache) -> list[str]:
    """Met les réponses épinglées dans le cache ; renvoie les questions disponibles."""
    if not FICHIER.exists():
        return []
    reponses = json.loads(FICHIER.read_text())
    for question, reponse in reponses.items():
        cache.ecrire(question, reponse)
    return list(reponses)


def calculer() -> int:
    reponses = {}
    for question, sql_reference in QUESTIONS.items():
        attendues = [list(ligne) for ligne in executer(sql_reference).lignes]
        for essai in range(1, ESSAIS + 1):
            reponse = repondre(question)
            if reponse.texte != TEXTE_ECHEC and reponse_correcte(
                attendues, reponse.requetes
            ):
                reponse.calculee_le = date.today().isoformat()
                reponses[question] = reponse.en_dict()
                break
        print(
            "OK   " if question in reponses else "ÉCHEC", f"(essai {essai})", question
        )
    FICHIER.write_text(
        json.dumps(reponses, ensure_ascii=False, indent=1, default=str) + "\n"
    )
    return 0 if len(reponses) == len(QUESTIONS) else 1


if __name__ == "__main__":
    sys.exit(calculer())
