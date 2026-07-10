#!/usr/bin/env bash
set -euo pipefail

cd sensor_output

if [ -d swatts ]; then
  rm -rf swatts
fi

mkdir swatts

source /opt/powerexp/venvs/smartwatts/bin/activate

python3 -m smartwatts   --input csv   --model HWPCReport   --files core.csv,msr.csv,rapl.csv   --name puller_csv   --output csv   --model PowerReport   --directory "$(pwd)/swatts/"   --name pusher_csv   --cpu-base-freq 2400   --cpu-tdp 150   --cpu-error-threshold 2.0   --sensor-reports-frequency 500

deactivate

cd ..

mv container_ids.txt ./sensor_output/
tar -czf smart_watts.tar.gz sensor_output

