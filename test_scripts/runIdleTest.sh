#!/usr/bin/env bash
set -euo pipefail

npx tsc -p ./tsconfig.json
ssh server_host 'cd /opt/powerexp && ./start_containers.sh && cd results && ./measure.sh'
sleep 500
scp confirmed_blocks.csv server_host:/opt/powerexp/results/sensor_output/
ssh server_host 'cd /opt/powerexp && ./stop_containers.sh && cd results && ./process.sh'
