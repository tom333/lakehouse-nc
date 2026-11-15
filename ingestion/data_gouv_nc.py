"""Source dlt : jeux de données de data.gouv.nc (API Explore v2.1 d'OpenDataSoft).

Chaque jeu est téléchargé en Parquet, filtré côté serveur sur un curseur de
date, puis fusionné (merge upsert) dans une table Iceberg du schéma bronze.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO

import dlt
import httpx
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

API = "https://data.gouv.nc/api/explore/v2.1/catalog/datasets"


@dataclass(frozen=True)
class Jeu:
    """Un jeu de data.gouv.nc et la façon de le charger en incrémental."""

    table: str
    dataset_id: str
    cle: tuple[str, ...]
    curseur: str
    # Fenêtre de recouvrement : le curseur de véhicules n'a que le jour, et un
    # transfert peut être publié après une transaction plus récente.
    recouvrement: timedelta


JEUX = (
    Jeu(
        table="vehicules_immatricules",
        dataset_id="vehicules-immatricules-nc",
        cle=("numero_immat",),
        curseur="date_mise_a_jour",
        recouvrement=timedelta(days=1),
    ),
    Jeu(
        table="transferts_vehicules_occasion",
        dataset_id="transferts-certificats-d-immatriculation-des-vehicules-d-occasion-nc",
        cle=("timestamp_transaction", "numero_immat"),
        curseur="timestamp_transaction",
        recouvrement=timedelta(days=3),
    ),
)


def telecharger(jeu: Jeu, depuis: datetime | None) -> pa.Table:
    """Export Parquet du jeu, restreint aux lignes dont le curseur >= depuis."""
    params = {}
    if depuis is not None:
        params["where"] = f"{jeu.curseur} >= date'{depuis.isoformat()}'"
    r = httpx.get(
        f"{API}/{jeu.dataset_id}/exports/parquet",
        params=params,
        timeout=600,
        follow_redirects=True,
    )
    r.raise_for_status()
    return pq.read_table(BytesIO(r.content))


def ressource(jeu: Jeu):
    @dlt.resource(
        name=jeu.table,
        primary_key=jeu.cle,
        write_disposition={"disposition": "merge", "strategy": "upsert"},
        table_format="iceberg",
    )
    def charger():
        etat = dlt.current.resource_state()
        dernier = etat.get("dernier_curseur")
        depuis = None
        if dernier is not None:
            depuis = datetime.fromisoformat(dernier) - jeu.recouvrement
        lignes = telecharger(jeu, depuis)
        if lignes.num_rows == 0:
            return
        # dlt n'enregistre l'état qu'avec un chargement réussi : un échec ne fait pas avancer le curseur.
        etat["dernier_curseur"] = pc.max(lignes.column(jeu.curseur)).as_py().isoformat()
        if dernier is None:
            # Premier chargement : dlt découpe l'upsert Iceberg en commits de
            # 1 000 lignes (lent sur tout un jeu) ; un replace n'en fait qu'un.
            yield dlt.mark.with_hints(
                lignes, dlt.mark.make_hints(write_disposition="replace")
            )
        else:
            yield lignes

    return charger


@dlt.source(name="data_gouv_nc")
def data_gouv_nc(tables: tuple[str, ...] | None = None):
    for jeu in JEUX:
        if tables is None or jeu.table in tables:
            yield ressource(jeu)
