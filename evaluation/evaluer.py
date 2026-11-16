"""Évalue l'agent sur les questions de référence, pour un ou plusieurs modèles.

Usage : uv run python -m evaluation.evaluer --modele nvidia/nemotron-3-ultra-550b-a55b:free
        [--modele google/gemma-4-31b-it:free] [--questions q01,q02]

Une réponse est correcte si les lignes renvoyées par l'agent contiennent celles du
SQL attendu (mêmes valeurs, ordre des colonnes indifférent, colonnes en plus
tolérées, même nombre de lignes), ou, pour une question à refuser, si l'agent
n'a exécuté aucune requête. Résultats : evaluation/resultats/<modele>.json et
evaluation/RESULTATS.md.
"""

import argparse
import json
import os
import re
import statistics
import time
import tomllib
from datetime import date
from pathlib import Path

from openai import OpenAI

from agent.agent import repondre
from agent.comparaison import reponse_correcte
from agent.modeles import OPENROUTER, Modele, gratuits_avec_outils
from agent.sql import executer

DOSSIER = Path(__file__).parent


class ModeleIndisponible(RuntimeError):
    """Le fournisseur refuse les appels (quota, saturation) : rien n'est publié."""


PAUSE_ENTRE_QUESTIONS = (
    4  # secondes : 20 requêtes par minute au plus sur les modèles gratuits
)


def evaluer_modele(nom: str, questions: list[dict]) -> dict:
    client = OpenAI(
        base_url=OPENROUTER,
        api_key=os.environ["OPENROUTER_API_KEY"],
        timeout=90,
        max_retries=0,
    )
    modele = Modele(nom, client)
    details = []
    for q in questions:
        if len(details) >= 2 and all(d["erreur_api"] for d in details[-2:]):
            raise ModeleIndisponible(
                f"{nom} : 2 questions consécutives en erreur d'API, évaluation abandonnée."
            )
        attendues = (
            None if q.get("refus") else [list(l) for l in executer(q["sql"]).lignes]
        )
        for essai in range(3):
            debut = time.monotonic()
            reponse = repondre(q["question"], [modele])
            # repondre() absorbe les erreurs d'API (quota, indisponibilité) : on réessaie.
            erreur = (
                "API indisponible" if reponse.texte.startswith("Aucun modèle") else None
            )
            if not erreur:
                break
            time.sleep(10 * (essai + 1))
        duree = round(time.monotonic() - debut, 1)
        if erreur:
            correcte = False
        elif q.get("refus"):
            correcte = reponse.sql is None
        else:
            # Correcte si une des requêtes exécutées renvoie le résultat attendu : l'agent
            # peut compléter sa réponse par une requête de contexte.
            correcte = reponse_correcte(attendues, reponse.requetes)
        details.append(
            {
                "id": q["id"],
                "question": q["question"],
                "correcte": correcte,
                "duree_s": duree,
                "erreur_api": erreur,
                "sql_executes": None
                if erreur
                else [r["sql"] for r in reponse.requetes],
                "lignes_agent": None if erreur else reponse.lignes[:20],
                "sql_attendu": q.get("sql"),
                "lignes_attendues": attendues[:20] if attendues else None,
            }
        )
        print(
            f"{nom} {q['id']} {'OK ' if correcte else 'KO '} {duree:5.1f} s {erreur or ''}"
        )
        time.sleep(PAUSE_ENTRE_QUESTIONS)
    reussies = sum(d["correcte"] for d in details)
    return {
        "modele": nom,
        "date": date.today().isoformat(),
        "questions": len(details),
        "correctes": reussies,
        "score": round(100 * reussies / len(details), 1),
        "duree_mediane_s": statistics.median(d["duree_s"] for d in details),
        "erreurs_api": sum(bool(d["erreur_api"]) for d in details),
        "details": details,
    }


def ecrire_synthese() -> None:
    resultats = [
        json.loads(f.read_text())
        for f in sorted((DOSSIER / "resultats").glob("*.json"))
    ]
    lignes = [
        "# Résultats de l'évaluation de l'agent",
        "",
        "Généré par `uv run python -m evaluation.evaluer`. Questions : `evaluation/questions.toml`.",
        "",
        "| Modèle | Date | Score | Correctes | Durée médiane | Erreurs d'API |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(resultats, key=lambda r: -r["score"]):
        lignes.append(
            f"| `{r['modele']}` | {r['date']} | **{r['score']} %** | {r['correctes']}/{r['questions']} "
            f"| {r['duree_mediane_s']} s | {r['erreurs_api']} |"
        )
    (DOSSIER / "RESULTATS.md").write_text("\n".join(lignes) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--modele", action="append", required=True)
    parser.add_argument("--questions", help="identifiants séparés par des virgules")
    args = parser.parse_args()

    questions = tomllib.loads((DOSSIER / "questions.toml").read_text())["question"]
    if args.questions:
        voulues = set(args.questions.split(","))
        questions = [q for q in questions if q["id"] in voulues]
    gratuits = gratuits_avec_outils()
    for nom in args.modele:
        if nom not in gratuits:
            raise SystemExit(f"{nom} n'est pas un modèle gratuit acceptant les outils.")
        try:
            resultat = evaluer_modele(nom, questions)
        except ModeleIndisponible as e:
            print(f"== {e}")
            continue
        # Seul un passage complet, sans erreur d'API, est publié : une erreur du
        # fournisseur ne dit rien de la qualité du modèle.
        if not args.questions and resultat["erreurs_api"] == 0:
            fichier = DOSSIER / "resultats" / (re.sub(r"[^\w.-]", "_", nom) + ".json")
            fichier.write_text(
                json.dumps(resultat, ensure_ascii=False, indent=1, default=str) + "\n"
            )
        print(
            f"== {nom} : {resultat['score']} % ({resultat['correctes']}/{resultat['questions']})"
        )
    ecrire_synthese()


if __name__ == "__main__":
    main()
