"""Choix du modèle : gratuits d'OpenRouter d'abord, LocalAI en repli.

La liste des modèles gratuits change souvent : on lit celle d'OpenRouter au
lieu de coder un identifiant en dur, et on écarte tout modèle payant, la clé
du compte pouvant payer.
"""

import os
import time
from dataclasses import dataclass

import httpx
from openai import OpenAI

OPENROUTER = "https://openrouter.ai/api/v1"
PREFERENCES = (
    "nvidia/nemotron-3-ultra-550b-a55b:free,google/gemma-4-31b-it:free,openrouter/free"
)
_catalogue: tuple[float, set[str]] = (0.0, set())


@dataclass
class Modele:
    nom: str
    client: OpenAI


def gratuits_avec_outils() -> set[str]:
    """Modèles gratuits d'OpenRouter acceptant les appels d'outils (cache 1 h)."""
    global _catalogue
    if time.monotonic() - _catalogue[0] > 3600:
        modeles = httpx.get(f"{OPENROUTER}/models", timeout=20).json()["data"]
        _catalogue = (
            time.monotonic(),
            {
                m["id"]
                for m in modeles
                if m["pricing"]["prompt"] == "0"
                and m["pricing"]["completion"] == "0"
                and "tools" in (m.get("supported_parameters") or [])
            },
        )
    return _catalogue[1]


def candidats() -> list[Modele]:
    """Modèles à essayer, dans l'ordre."""
    resultat = []
    if cle := os.environ.get("OPENROUTER_API_KEY"):
        client = OpenAI(base_url=OPENROUTER, api_key=cle, timeout=60, max_retries=0)
        preferes = [
            n.strip()
            for n in os.environ.get("OPENROUTER_MODELS", PREFERENCES).split(",")
        ]
        gratuits = gratuits_avec_outils()
        resultat += [Modele(nom, client) for nom in preferes if nom in gratuits]
    if cle := os.environ.get("LOCALAI_API_KEY"):
        client = OpenAI(
            base_url=os.environ.get(
                "LOCALAI_URL", "http://localai.localai.svc.cluster.local:8080/v1"
            ),
            api_key=cle,
            timeout=120,
            max_retries=0,
        )
        resultat.append(
            Modele(os.environ.get("LOCALAI_MODEL", "qwen2.5-7b-instruct"), client)
        )
    return resultat
