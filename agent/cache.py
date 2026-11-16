"""Cache des réponses par question normalisée et quota quotidien de questions.

Les modèles gratuits sont plafonnés : une question déjà posée est servie depuis
le cache, et le nombre de questions envoyées au modèle par jour est limité.
"""

import json
import re
import sqlite3
import threading
import unicodedata
from datetime import date


def normaliser(question: str) -> str:
    """Minuscules, sans accents ni ponctuation, espaces réduits."""
    texte = unicodedata.normalize("NFKD", question.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", texte)).strip()


class Cache:
    def __init__(self, chemin: str = ":memory:"):
        self._verrou = threading.Lock()
        self._db = sqlite3.connect(chemin, check_same_thread=False)
        self._db.executescript(
            "CREATE TABLE IF NOT EXISTS reponses (question TEXT PRIMARY KEY, reponse TEXT);"
            "CREATE TABLE IF NOT EXISTS quota (jour TEXT PRIMARY KEY, questions INTEGER);"
        )

    def lire(self, question: str) -> dict | None:
        with self._verrou:
            ligne = self._db.execute(
                "SELECT reponse FROM reponses WHERE question = ?",
                (normaliser(question),),
            ).fetchone()
        return json.loads(ligne[0]) if ligne else None

    def ecrire(self, question: str, reponse: dict) -> None:
        with self._verrou, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO reponses VALUES (?, ?)",
                (normaliser(question), json.dumps(reponse, default=str)),
            )

    def consommer(self, maximum: int) -> bool:
        """Compte une question du jour ; False si le quota est atteint."""
        jour = date.today().isoformat()
        with self._verrou, self._db:
            ligne = self._db.execute(
                "SELECT questions FROM quota WHERE jour = ?", (jour,)
            ).fetchone()
            n = ligne[0] if ligne else 0
            if n >= maximum:
                return False
            self._db.execute(
                "INSERT OR REPLACE INTO quota VALUES (?, ?)", (jour, n + 1)
            )
        return True
