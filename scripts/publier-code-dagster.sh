#!/usr/bin/env bash
# Construit et publie l'image du code Dagster, puis recharge le serveur de code.
# On supprime le pod plutôt que `kubectl rollout restart` : ArgoCD (selfHeal)
# annulerait l'annotation de redémarrage et relancerait un second déploiement.
set -euo pipefail
cd "$(dirname "$0")/.."
image=localhost:32000/lakehouse-nc-dagster:latest
docker build -t "$image" .
docker push "$image"
kubectl -n dagster delete pod -l component=lakehouse-nc
kubectl -n dagster rollout status deploy/dagster-code-lakehouse-nc --timeout=300s
echo "Penser à recharger l'emplacement « lakehouse-nc » dans l'interface Dagster."
