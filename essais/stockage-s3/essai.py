# /// script
# requires-python = ">=3.12"
# dependencies = ["pyiceberg[pyarrow,s3fs]", "boto3", "httpx"]
# ///
"""Essai réel : Iceberg sur RustFS via le catalogue Lakekeeper.

Clés RustFS lues dans l'environnement (RUSTFS_ACCESS_KEY, RUSTFS_SECRET_KEY),
jamais écrites sur disque.
"""

import os

import boto3
import httpx
import pyarrow as pa
from pyiceberg.catalog.rest import RestCatalog

ENDPOINT = "https://rustfs.tgu.ovh"
BUCKET = "lakehouse-nc"
WAREHOUSE = "essai"
LAKEKEEPER = "http://localhost:8181"
ACCESS = os.environ["RUSTFS_ACCESS_KEY"]
SECRET = os.environ["RUSTFS_SECRET_KEY"]


def creer_bucket() -> None:
    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS,
        aws_secret_access_key=SECRET,
        region_name="us-east-1",
    )
    if BUCKET not in [b["Name"] for b in s3.list_buckets()["Buckets"]]:
        s3.create_bucket(Bucket=BUCKET)
    print(f"bucket {BUCKET} : ok")


def creer_warehouse() -> None:
    r = httpx.post(
        f"{LAKEKEEPER}/management/v1/bootstrap", json={"accept-terms-of-use": True}
    )
    print("bootstrap :", r.status_code)
    r = httpx.post(
        f"{LAKEKEEPER}/management/v1/warehouse",
        timeout=60,
        json={
            "warehouse-name": WAREHOUSE,
            "storage-credential": {
                "type": "s3",
                "credential-type": "access-key",
                "aws-access-key-id": ACCESS,
                "aws-secret-access-key": SECRET,
            },
            "storage-profile": {
                "type": "s3",
                "bucket": BUCKET,
                "region": "us-east-1",
                "endpoint": ENDPOINT,
                "path-style-access": True,
                "sts-enabled": False,
                "remote-signing-enabled": True,
                "flavor": "s3-compat",
                "key-prefix": WAREHOUSE,
            },
            "delete-profile": {"type": "hard"},
        },
    )
    print("warehouse :", r.status_code, r.text[:300])
    if r.status_code != 409:  # 409 : warehouse déjà créé par un essai précédent
        r.raise_for_status()


def catalogue(mode: str) -> RestCatalog:
    props = {
        "uri": f"{LAKEKEEPER}/catalog",
        "warehouse": WAREHOUSE,
        "header.X-Iceberg-Access-Delegation": mode,
    }
    if mode == "client-managed":
        props |= {
            "s3.endpoint": ENDPOINT,
            "s3.access-key-id": ACCESS,
            "s3.secret-access-key": SECRET,
            "s3.region": "us-east-1",
            "s3.force-virtual-addressing": "false",
        }
    else:  # remote-signing : seul le FileIO fsspec sait signer via le catalogue
        props["py-io-impl"] = "pyiceberg.io.fsspec.FsspecFileIO"
    return RestCatalog(f"lk-{mode}", **props)


def essai(mode: str) -> None:
    print(f"\n== mode {mode} ==")
    cat = catalogue(mode)
    ns = ("essai",)
    cat.create_namespace_if_not_exists(ns)
    ident = (*ns, mode.replace("-", "_"))
    if cat.table_exists(ident):
        cat.purge_table(ident)
    lot1 = pa.table({"id": [1, 2, 3], "marque": ["Toyota", "Renault", "Peugeot"]})
    lot2 = pa.table({"id": [4], "marque": ["Dacia"]})
    t = cat.create_table(ident, schema=lot1.schema)
    t.append(lot1)
    t.append(lot2)
    t = cat.load_table(ident)
    lu = t.scan().to_arrow()
    print("emplacement :", t.location())
    print("lignes relues :", lu.num_rows, "| snapshots :", len(t.snapshots()))
    assert lu.num_rows == 4 and len(t.snapshots()) == 2
    cat.purge_table(ident)
    print("purge : ok")


if __name__ == "__main__":
    creer_bucket()
    creer_warehouse()
    for mode in ("client-managed", "remote-signing"):
        try:
            essai(mode)
        except Exception as e:  # noqa: BLE001 — on veut le résultat des deux modes
            print(f"ÉCHEC {mode} : {type(e).__name__}: {e}"[:600])
