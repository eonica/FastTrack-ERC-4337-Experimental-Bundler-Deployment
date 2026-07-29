#!/usr/bin/env bash
set -euo pipefail

echo "Native Tests"

ssh proxmox 'cd /opt/powerexp && ./start_native.sh && cd results && ./measure.sh'
sleep 420
scp confirmed_blocks.csv proxmox:/opt/powerexp/results/sensor_output/
ssh proxmox 'cd /opt/powerexp && ./stop_native.sh && cd results && ./native_process.sh'
