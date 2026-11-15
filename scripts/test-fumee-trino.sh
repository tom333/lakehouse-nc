#!/usr/bin/env bash
# Test de fumée : Trino écrit et relit une table Iceberg via Lakekeeper et RustFS.
# Usage : scripts/test-fumee-trino.sh   (contexte kubectl pointé sur le cluster)
set -euo pipefail
trino() { kubectl -n lakehouse-nc exec deploy/trino-coordinator -- trino --output-format=TSV --execute "$1"; }
trino "CREATE SCHEMA IF NOT EXISTS lakehouse.fumee"
trino "DROP TABLE IF EXISTS lakehouse.fumee.essai"
trino "CREATE TABLE lakehouse.fumee.essai (id integer, marque varchar)"
trino "INSERT INTO lakehouse.fumee.essai VALUES (1, 'Toyota'), (2, 'Renault')"
trino "INSERT INTO lakehouse.fumee.essai VALUES (3, 'Dacia')"
n=$(trino "SELECT count(*) FROM lakehouse.fumee.essai")
s=$(trino "SELECT count(*) FROM lakehouse.fumee.\"essai\$snapshots\"")
# 3 snapshots : CREATE TABLE (vide) + 2 INSERT
echo "lignes=$n snapshots=$s"
trino "DROP TABLE lakehouse.fumee.essai"
trino "DROP SCHEMA lakehouse.fumee"
[ "$n" = 3 ] && [ "$s" = 3 ] && echo "OK" || { echo "ÉCHEC"; exit 1; }
