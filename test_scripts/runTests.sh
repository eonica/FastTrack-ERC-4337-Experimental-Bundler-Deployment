#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./runTests.sh [SCA_NUMBER] [THROTTLE_TIME] [ROUNDS_TOTAL] [BLOCK_TIME]
#
# Example:
#   ./runTests.sh
#   ./runTests.sh 50 100 20
#   ./runTests.sh 50 100 20 5

if (( $# > 4 )); then
  echo "Usage: $0 [SCA_NUMBER] [THROTTLE_TIME] [ROUNDS_TOTAL] [BLOCK_TIME]" >&2
  exit 1
fi

SCA_NUMBER="${1:-100}"
THROTTLE_TIME="${2:-25}"
ROUNDS_TOTAL="${3:-10}"
BLOCK_TIME="${4:-}"

if [[ -n "$BLOCK_TIME" && ! "$BLOCK_TIME" =~ ^[1-9][0-9]*$ ]]; then 
  echo "Error: BLOCK_TIME must be a positive integer." >&2 
  exit 1 
fi

npx tsc -p ./tsconfig.json

if [[ -n "$BLOCK_TIME" ]]; then 
  ssh server_host "cd /opt/powerexp && ./start_containers.sh container_ids.txt '$BLOCK_TIME' && cd results && ./measure.sh" 
else
  ssh server_host 'cd /opt/powerexp && ./start_containers.sh && cd results && ./measure.sh'
fi

sleep 3

node transferUserOpRoundsThrottled.js \
  "$SCA_NUMBER" \
  "$THROTTLE_TIME" \
  "$ROUNDS_TOTAL"
  
scp confirmed_blocks.csv server_host:/opt/powerexp/results/sensor_output/
ssh server_host "cd /opt/powerexp && ./stop_containers.sh && cd results && ./process.sh '$SCA_NUMBER' '$THROTTLE_TIME' '$ROUNDS_TOTAL' '${BLOCK_TIME:-12}'"
