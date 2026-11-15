"""Charge les jeux de data.gouv.nc dans le schéma bronze du lac Iceberg.

Usage : uv run python -m ingestion.pipeline [table ...]

Variables d'environnement :
  S3_ACCESS_KEY, S3_SECRET_KEY  clés du stockage RustFS (obligatoires)
  LAKEKEEPER_URI                catalogue REST (défaut : service du cluster)
  S3_ENDPOINT                   RustFS (défaut : service du cluster)
"""

import os
import sys

import dlt

from ingestion.data_gouv_nc import data_gouv_nc

WAREHOUSE = "lakehouse"
BUCKET = "s3://lakehouse-nc"


def configurer() -> None:
    uri = os.environ.get(
        "LAKEKEEPER_URI",
        "http://lakekeeper.lakehouse-nc.svc.cluster.local:8181/catalog",
    )
    endpoint = os.environ.get(
        "S3_ENDPOINT", "http://rustfs-svc.ia-lab.svc.cluster.local:9000"
    )
    cle, secret = os.environ["S3_ACCESS_KEY"], os.environ["S3_SECRET_KEY"]
    dlt.secrets["destination.filesystem.credentials"] = {
        "aws_access_key_id": cle,
        "aws_secret_access_key": secret,
        "endpoint_url": endpoint,
        "region_name": "us-east-1",
    }
    dlt.config["iceberg_catalog.iceberg_catalog_type"] = "rest"
    dlt.secrets["iceberg_catalog.iceberg_catalog_config"] = {
        "type": "rest",
        "uri": uri,
        "warehouse": WAREHOUSE,
        # Le client garde ses propres clés S3 (comme Trino) : pas de signature
        # déléguée ni d'identifiants délivrés par le catalogue.
        "header.X-Iceberg-Access-Delegation": "client-managed",
        "s3.endpoint": endpoint,
        "s3.access-key-id": cle,
        "s3.secret-access-key": secret,
        "s3.region": "us-east-1",
        "s3.force-virtual-addressing": "false",
    }


def creer_pipeline() -> dlt.Pipeline:
    """Pipeline dlt vers bronze ; appeler configurer() avant de le lancer."""
    return dlt.pipeline(
        pipeline_name="data_gouv_nc",
        destination=dlt.destinations.filesystem(bucket_url=BUCKET),
        dataset_name="bronze",
    )


def main(tables: list[str]) -> None:
    configurer()
    print(creer_pipeline().run(data_gouv_nc(tuple(tables) or None)))


if __name__ == "__main__":
    main(sys.argv[1:])
