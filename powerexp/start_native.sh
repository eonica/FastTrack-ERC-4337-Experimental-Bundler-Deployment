#!/usr/bin/env bash
set -euo pipefail

BLOCK_TIME="${1:-12}"
ANVIL_LOG_FILE="/tmp/anvil-8545.log"
ALTO_LOG_FILE="/tmp/alto-3000.log"

if [[ ! "$BLOCK_TIME" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: BLOCK_TIME must be a positive integer." >&2
  exit 1
fi

ALTO_CONFIG="alto-config.json"

if [[ "$BLOCK_TIME" == "6" ]]; then
  ALTO_CONFIG="alto-config-6.json"
elif [[ "$BLOCK_TIME" == "2" ]]; then
  ALTO_CONFIG="alto-config-2.json"
fi

systemd-run \
  --scope \
  --slice=user.slice \
  --unit=anvil \
  /root/.foundry/bin/anvil \
    --host 0.0.0.0 \
    --port 8545 \
    --chain-id 1337 \
    --block-time "$BLOCK_TIME" \
    --gas-limit 30000000 \
    --gas-price 1 \
    --block-base-fee-per-gas 0 \
    --load-state /opt/powerexp/state/state_light.json \
    --dump-state /opt/powerexp/state/state_light.json \
    --disable-code-size-limit \
    --quiet \
  >"$ANVIL_LOG_FILE" 2>&1 &

echo "Anvil started"

sleep 3

cd /opt/powerexp/alto_native/alto

systemd-run \
  --scope \
  --slice=user.slice \
  --unit=alto \
  /root/.nvm/versions/node/v24.18.0/bin/node src/esm/cli/alto.js run --config "$ALTO_CONFIG" --log-level "fatal" \
  >"$ALTO_LOG_FILE" 2>&1 &

echo "Alto started"


