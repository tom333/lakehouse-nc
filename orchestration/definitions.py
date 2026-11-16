"""Définitions Dagster : ingestion dlt en bronze, puis modèles dbt silver et gold.

Les assets dlt portent les clés bronze/<table>, celles des sources dbt : Dagster
enchaîne donc les modèles dbt après l'ingestion des tables dont ils dépendent.
"""

from pathlib import Path

from dagster import (
    AssetExecutionContext,
    AssetKey,
    AssetSelection,
    AssetSpec,
    DefaultScheduleStatus,
    Definitions,
    ScheduleDefinition,
    define_asset_job,
)
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets
from dagster_dlt import DagsterDltResource, DagsterDltTranslator, dlt_assets
from dagster_dlt.translator import DltResourceTranslatorData

from ingestion.data_gouv_nc import data_gouv_nc
from ingestion.pipeline import configurer, creer_pipeline

projet_dbt = DbtProject(
    project_dir=Path(__file__).parent.parent / "transformation",
    profiles_dir=Path(__file__).parent.parent / "transformation",
)
projet_dbt.prepare_if_dev()


class TraducteurBronze(DagsterDltTranslator):
    def get_asset_spec(self, data: DltResourceTranslatorData) -> AssetSpec:
        return (
            super()
            .get_asset_spec(data)
            .replace_attributes(key=AssetKey(["bronze", data.resource.name]), deps=[])
        )


@dlt_assets(
    dlt_source=data_gouv_nc(),
    dlt_pipeline=creer_pipeline(),
    name="data_gouv_nc",
    group_name="bronze",
    dagster_dlt_translator=TraducteurBronze(),
)
def bronze(context: AssetExecutionContext, dlt: DagsterDltResource):
    configurer()
    yield from dlt.run(context=context)


@dbt_assets(manifest=projet_dbt.manifest_path)
def modeles_dbt(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()


quotidien = define_asset_job("quotidien", selection=AssetSelection.all())

defs = Definitions(
    assets=[bronze, modeles_dbt],
    jobs=[quotidien],
    schedules=[
        ScheduleDefinition(
            job=quotidien,
            cron_schedule="0 6 * * *",
            execution_timezone="Pacific/Noumea",
            default_status=DefaultScheduleStatus.RUNNING,
        )
    ],
    resources={
        "dlt": DagsterDltResource(),
        "dbt": DbtCliResource(project_dir=projet_dbt),
    },
)
