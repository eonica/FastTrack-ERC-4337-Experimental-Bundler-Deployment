#!/usr/bin/env bash
set -euo pipefail

systemctl stop anvil.scope
echo "Anvil stopped"

systemctl stop alto.scope
echo "Alto stopped"

docker stop hwpc-sensor
echo "HWPC stopped"
