from decimal import Decimal

from agent.comparaison import comparer


def test_valeur_unique_et_colonnes_en_plus():
    assert comparer([[1264]], [["Électrique", 1264]])


def test_ordre_des_lignes_et_colonnes_indifferent():
    assert comparer([["Sud", 10], ["Nord", 5]], [[5, "nord"], [10, "SUD"]])


def test_nombre_de_lignes_different():
    assert not comparer([["Sud", 10]], [["Sud", 10], ["Nord", 5]])


def test_valeur_fausse():
    assert not comparer([[1264]], [[1265]])


def test_arrondi_et_pourcentage_en_fraction():
    assert comparer([[Decimal("81.9")]], [[81.93]])
    assert comparer([[81.9]], [[0.819]])
