#!/usr/bin/env bash
set -euo pipefail

echo "Native Tests"

# Usage:
#   ./runNativeTests.sh [SCA_NUMBER] [THROTTLE_TIME] [ROUNDS_TOTAL] [BLOCK_TIME] [TEST_COUNTER]
#

if (( $# > 5 )); then
  echo "Usage: $0 [SCA_NUMBER] [THROTTLE_TIME] [ROUNDS_TOTAL] [BLOCK_TIME] [TEST_COUNTER]" >&2
  exit 1
fi

SCA_NUMBER="${1:-100}"
THROTTLE_TIME="${2:-25}"
ROUNDS_TOTAL="${3:-10}"
BLOCK_TIME="${4:-12}"
TEST_COUNTER="${5:-0}"

if [[ -n "$BLOCK_TIME" && ! "$BLOCK_TIME" =~ ^[1-9][0-9]*$ ]]; then 
  echo "Error: BLOCK_TIME must be a positive integer." >&2 
  exit 1 
fi

npx tsc -p ./tsconfig.json
# ssh root@10.100.32.56 

ssh proxmox "cd /opt/powerexp && ./start_native.sh '$BLOCK_TIME' && cd results && ./measure.sh" 

sleep 3

node transferUserOpRoundsThrottled.js \
  "$SCA_NUMBER" \
  "$THROTTLE_TIME" \
  "$ROUNDS_TOTAL"

scp confirmed_blocks.csv proxmox:/opt/powerexp/results/sensor_output/
ssh proxmox "cd /opt/powerexp && ./stop_native.sh && cd results && ./native_process.sh '$SCA_NUMBER' '$THROTTLE_TIME' '$ROUNDS_TOTAL' '${BLOCK_TIME:-12}' '$TEST_COUNTER'"
