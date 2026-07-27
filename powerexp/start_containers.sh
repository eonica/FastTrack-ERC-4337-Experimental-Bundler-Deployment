set -euo pipefail

OUT_FILE="${1:-container_ids.txt}"

BLOCK_TIME="${2:-}"

if (( $# > 2 )); then
  echo "Usage: $0 [OUT_FILE] [BLOCK_TIME_SECONDS]" >&2
  exit 1
fi

ANVIL_ARGS=()

if [[ -n "$BLOCK_TIME" ]]; then
  if [[ ! "$BLOCK_TIME" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: BLOCK_TIME_SECONDS must be a positive integer." >&2
    exit 1
  fi

  # Supplying arguments to docker run replaces the Dockerfile CMD,
  # so all original Anvil arguments must be repeated here.
  ANVIL_ARGS=(
    --host 0.0.0.0
    --port 8545
    --chain-id 1337
    --block-time "$BLOCK_TIME"
    --gas-limit 30000000
    --gas-price 1
    --block-base-fee-per-gas 0
    --load-state /var/lib/anvil/state.json
    --dump-state /var/lib/anvil/state.json
    --disable-code-size-limit
    --quiet
  )
fi

echo "Starting containers..."
if [[ -n "$BLOCK_TIME" ]]; then
  echo "Anvil block interval: ${BLOCK_TIME} seconds"
else
  echo "Anvil block interval: Dockerfile default (12 seconds)"
fi


# Optional cleanup if old containers with the same names exist
docker rm -f anvil alto >/dev/null 2>&1 || true

ANVIL_ID=$(
  docker run --rm -d \
    --name anvil \
    --network aa-exp \
    -v /opt/powerexp/state/state.json:/var/lib/anvil/state.json \
    -p 8545:8545 \
    anvil-debian-slim:local \
    "${ANVIL_ARGS[@]}" 
)

ALTO_ID=$(
  docker run --rm -d \
    --name alto \
    --network aa-exp \
    -p 3000:3000 \
    alto-debian-slim:local 
)

{
  echo "timestamp=$(date --iso-8601=seconds)"
  echo "anvil=$ANVIL_ID"
  echo "alto=$ALTO_ID"
  echo
  echo "anvil_cgroup=$(cat /proc/$(docker inspect -f '{{.State.Pid}}' anvil)/cgroup | cut -d: -f3)"
  echo "alto_cgroup=$(cat /proc/$(docker inspect -f '{{.State.Pid}}' alto)/cgroup | cut -d: -f3)"
} > "$OUT_FILE"

echo "Started containers:"
echo "  anvil: $ANVIL_ID"
echo "  alto:  $ALTO_ID"
echo "Wrote IDs to: $OUT_FILE"

mv $OUT_FILE ./results/
