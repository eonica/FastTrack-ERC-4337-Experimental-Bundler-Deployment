#!/usr/bin/env bash
set -euo pipefail

# ==== CONFIGURATION ====
RPC_URL="http://127.0.0.1:8545"
RECIPIENTS_FILE="${1:-recipients.txt}"

# Amount to send to each recipient.
# You can override it as the second argument, e.g.:
# ./fund_recipients.sh recipients.txt 0.1ether
VALUE="${2:-1ether}"

# 10 senders; each sender funds 10 consecutive recipients.
SENDERS=(
  0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
  0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
  0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
  0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6
  0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a
  0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba
  0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e
  0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356
  0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97
  0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6
)

RECIPIENTS_PER_SENDER=10
EXPECTED_RECIPIENTS=$(( ${#SENDERS[@]} * RECIPIENTS_PER_SENDER ))

# ==== LOAD RECIPIENTS ====
if [ ! -f "$RECIPIENTS_FILE" ]; then
  echo "Error: recipients file not found: $RECIPIENTS_FILE"
  exit 1
fi

mapfile -t RECIPIENTS < <(
  sed -E 's/^[[:space:]]*"?(0x[a-fA-F0-9]{40})"?[[:space:]]*$/\1/' "$RECIPIENTS_FILE" |
  grep -E '^0x[a-fA-F0-9]{40}$'
)

if [ "${#RECIPIENTS[@]}" -ne "$EXPECTED_RECIPIENTS" ]; then
  echo "Error: expected $EXPECTED_RECIPIENTS recipient addresses, got ${#RECIPIENTS[@]}"
  exit 1
fi

echo "Funding ${#RECIPIENTS[@]} recipients with $VALUE each"
echo "Using ${#SENDERS[@]} senders, $RECIPIENTS_PER_SENDER recipients per sender"
echo

# ==== EXECUTION ====
send_batch() {
  local sender_index="$1"
  local sender="${SENDERS[$sender_index]}"
  local start=$(( sender_index * RECIPIENTS_PER_SENDER ))
  local end=$(( start + RECIPIENTS_PER_SENDER - 1 ))

  echo "[sender $sender_index] Starting recipients $start..$end"

  for recipient_index in $(seq "$start" "$end"); do
    local recipient="${RECIPIENTS[$recipient_index]}"

    echo "[sender $sender_index] Sending $VALUE to $recipient"

    cast send "$recipient" \
      --value "$VALUE" \
      --private-key "$sender" \
      --rpc-url "$RPC_URL"

    echo "[sender $sender_index] Sent to $recipient"
  done

  echo "[sender $sender_index] Done"
}

pids=()

for i in "${!SENDERS[@]}"; do
  send_batch "$i" &
  pids+=("$!")
done

failed=0

for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done

if [ "$failed" -ne 0 ]; then
  echo "One or more sender batches failed"
  exit 1
fi

echo
echo "All transfers completed successfully"
