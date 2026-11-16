import pytest

from agent.sql import RequeteRefusee, valider

ACCEPTEES = [
    "SELECT count(*) FROM fct_transferts",
    "SELECT * FROM gold.dim_commune",
    "SELECT * FROM lakehouse.gold.dim_commune",
    "WITH t AS (SELECT commune FROM fct_transferts) SELECT commune, count(*) FROM t GROUP BY 1",
    "SELECT 1 UNION ALL SELECT 2",
    "SELECT f.marque FROM fct_immatriculations f JOIN dim_energie e ON e.code_energie = f.code_energie",
    "SELECT * FROM (SELECT commune FROM dim_commune) s",
]

REFUSEES = [
    ("DROP TABLE gold.dim_commune", "lectures"),
    ("INSERT INTO gold.dim_commune VALUES ('X', 'Sud')", "lectures"),
    ("DELETE FROM gold.dim_commune", "lectures"),
    ("CREATE TABLE gold.x AS SELECT 1", "lectures"),
    ("CALL system.sync_partition_metadata('a', 'b', 'FULL')", "lectures"),
    ("SET SESSION query_max_run_time = '1h'", "lectures"),
    ("SHOW TABLES", "lectures"),
    ("SELECT 1; DROP TABLE gold.dim_commune", "seule instruction"),
    ("SELECT * FROM bronze.vehicules_immatricules", "hors du schéma"),
    ("SELECT * FROM silver.silver_vehicules", "hors du schéma"),
    ("SELECT * FROM system.runtime.queries", "hors du schéma"),
    ("SELECT * FROM autre.gold.dim_commune", "hors du schéma"),
    (
        "SELECT * FROM dim_commune WHERE commune IN (SELECT commune FROM bronze.x)",
        "hors du schéma",
    ),
    ("WITH t AS (SELECT * FROM bronze.x) SELECT * FROM t", "hors du schéma"),
    ("SELECT * FROM TABLE(system.query(query => 'SELECT 1'))", "fonctions de table"),
    ("SELECT FROM WHERE", "illisible"),
]


@pytest.mark.parametrize("sql", ACCEPTEES)
def test_lectures_gold_acceptees(sql):
    assert valider(sql)


@pytest.mark.parametrize(("sql", "motif"), REFUSEES)
def test_requetes_refusees(sql, motif):
    with pytest.raises(RequeteRefusee, match=motif):
        valider(sql)


def test_limite_ajoutee_si_absente():
    assert valider("SELECT * FROM dim_commune", lignes_max=50).endswith("LIMIT 50")


def test_limite_plafonnee():
    assert valider("SELECT * FROM dim_commune LIMIT 5000", lignes_max=50).endswith(
        "LIMIT 50"
    )


def test_limite_inferieure_conservee():
    assert valider("SELECT * FROM dim_commune LIMIT 10", lignes_max=50).endswith(
        "LIMIT 10"
    )
