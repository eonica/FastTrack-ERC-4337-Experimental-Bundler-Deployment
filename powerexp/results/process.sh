#!/usr/bin/env bash
set -euo pipefail

SCA_NUMBER="${1:-0}" 
THROTTLE_TIME="${2:-0}" 
ROUNDS_TOTAL="${3:-0}" 
BLOCK_TIME="${4:-0}"
TEST_COUNTER="${5:-0}"

ARCHIVE_NAME="swresults${TEST_COUNTER}_sca${SCA_NUMBER}_thr${THROTTLE_TIME}_rnd${ROUNDS_TOTAL}_bt${BLOCK_TIME}.tar.gz"


echo "=== Processing configuration ==="
echo "SCA_NUMBER:    $SCA_NUMBER"
echo "THROTTLE_TIME: $THROTTLE_TIME ms"
echo "ROUNDS_TOTAL:  $ROUNDS_TOTAL"
echo "BLOCK_TIME:    $BLOCK_TIME seconds"
echo "ARCHIVE:       $ARCHIVE_NAME"
echo "================================"

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
cp config_file.json ./sensor_output/

rm -f "$ARCHIVE_NAME"
tar -czf "$ARCHIVE_NAME" sensor_output

echo "Created archive: $(pwd)/$ARCHIVE_NAME"

# tar -czf smart_watts.tar.gz sensor_output

