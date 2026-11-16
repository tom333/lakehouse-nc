import json
from types import SimpleNamespace

import pytest

from agent import agent, graphique
from agent.cache import Cache, normaliser
from agent.modeles import Modele
from agent.sql import Resultat

RESULTAT = Resultat(
    sql="SELECT annee, n FROM t LIMIT 1000",
    colonnes=["annee", "n"],
    lignes=[(2023, 10), (2024, 12)],
)


def test_graphique_barres():
    figure = graphique.construire(
        RESULTAT, {"type": "barres", "x": "annee", "y": "n", "titre": "T"}
    )
    assert list(figure.data[0].y) == [10, 12]


@pytest.mark.parametrize(
    ("description", "motif"),
    [
        ({"type": "radar", "x": "annee", "y": "n"}, "inconnu"),
        ({"type": "barres", "x": "annee", "y": "z"}, "absente"),
    ],
)
def test_graphique_refuse(description, motif):
    with pytest.raises(graphique.GraphiqueRefuse, match=motif):
        graphique.construire(RESULTAT, description)


def test_normalisation():
    assert (
        normaliser("  Combien de VÉHICULES électriques ?")
        == "combien de vehicules electriques"
    )


def test_cache_et_quota():
    cache = Cache()
    assert cache.lire("q") is None
    cache.ecrire("Q ?", {"texte": "ok"})
    assert cache.lire("q") == {"texte": "ok"}
    assert cache.consommer(2) and cache.consommer(2) and not cache.consommer(2)


def _client_scripte(messages_modele):
    """Faux client OpenAI qui renvoie les messages prévus, dans l'ordre."""
    reponses = iter(messages_modele)

    def create(**_):
        return SimpleNamespace(choices=[SimpleNamespace(message=next(reponses))])

    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


def _message(contenu=None, appels=()):
    tool_calls = [
        SimpleNamespace(id=f"a{i}", function=SimpleNamespace(arguments=json.dumps(a)))
        for i, a in enumerate(appels)
    ] or None
    return SimpleNamespace(
        content=contenu,
        tool_calls=tool_calls,
        model_dump=lambda **_: {"role": "assistant"},
    )


@pytest.fixture
def sans_trino(monkeypatch):
    monkeypatch.setattr(agent, "consignes", lambda: "consignes")
    monkeypatch.setattr(agent.sql, "executer", lambda requete: RESULTAT)


def test_boucle_requete_puis_reponse(sans_trino):
    client = _client_scripte(
        [
            _message(
                appels=[
                    {
                        "sql": "SELECT 1",
                        "graphique": {"type": "lignes", "x": "annee", "y": "n"},
                    }
                ]
            ),
            _message("12 ventes en 2024."),
        ]
    )
    reponse = agent._converser(Modele("m:free", client), "question")
    assert reponse.texte == "12 ventes en 2024."
    assert reponse.sql == RESULTAT.sql and reponse.figure


def test_requete_refusee_renvoyee_au_modele(monkeypatch):
    monkeypatch.setattr(agent, "consignes", lambda: "consignes")
    message = agent._appel_outil(
        json.dumps({"sql": "DROP TABLE gold.x"}), agent.Reponse(texte="")
    )
    assert message.startswith("Requête refusée")


def test_cache_servi_sans_modele(monkeypatch):
    monkeypatch.setattr(
        agent, "repondre", lambda q: pytest.fail("le modèle ne doit pas être appelé")
    )
    cache = Cache()
    cache.ecrire("q", agent.Reponse(texte="en cache", sql="SELECT 1").en_dict())
    reponse, depuis_cache = agent.repondre_avec_cache("Q", cache, 10)
    assert depuis_cache and reponse.texte == "en cache"
