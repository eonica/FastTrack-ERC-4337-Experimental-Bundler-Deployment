import { createPublicClient, http, encodeFunctionData, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { createBundlerClient } from "viem/account-abstraction";
import TestTokenAbi from "./TestToken.abi.json" with { type: "json" };
import fs from "fs";

// -----------------------------
// Configuration
// -----------------------------
const CHAIN_RPC = "http://127.0.0.1:8545";     // Anvil
const BUNDLER_RPC = "http://127.0.0.1:3000";   // Alto bundler
const CONFIRMED_BLOCKS_LOG_FILE = "./confirmed_blocks.csv";

const ENTRYPOINT = {
  address: "0x5FbDB2315678afecb367f032d93F642f64180aa3" as `0x${string}`,
  version: "0.7" as const
};

// Test Configs:
// Test#1 50 rounds; 100 SCA(UserOps); 25 throttle
// Test#2 50 rounds; 100 SCA(UserOps); 50 throttle
// Test#3 50 rounds; 100 SCA(UserOps); 100 throttle
// Test#4 50 rounds; 75 SCA(UserOps); 25 throttle
// Test#5 50 rounds; 50 SCA(UserOps); 25 throttle
// Test#6 50 rounds; 25 SCA(UserOps); 25 throttle
// Test#7 100 rounds; 100 SCA(UserOps); 25 throttle; Block time 6 seconds (to config in Anvil Dockerfile and re-build)
// Test#8 300 rounds; 100 SCA(UserOps); 25 throttle; Block time 2 seconds (to config in Anvil Dockerfile and re-build)
// Test#9 runIdleTest for idle measurement (no UserOps processing)


// Number of SCAs exchanging tokens 
const SCA_NUMBER = 100;

// time to wait between UserOps individual dispatches
const THROTTLE_TIME = 25;

// rounds of transfers
const ROUNDS_TOTAL = 35;

const SCAS_PER_OWNER = 10;

// Path can be overridden as first CLI argument:
//   tsx script.ts simpleAccountAddresses.json
const SIMPLE_ACCOUNT_ADDRESSES_FILE = "./created_accounts_salt_0x0A.json";

const SIMPLE_ACCOUNT_ADDRESSES = loadSimpleAccountAddresses(
  SIMPLE_ACCOUNT_ADDRESSES_FILE,
  SCA_NUMBER
);

const SCA_OWNERS_NUMBER = 10;

const SIMPLE_ACCOUNT_OWNER_KEYS: `0x${string}`[] = [
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
    "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",
    "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",
    "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",
    "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",
    "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6"
];

const ERC20_ADDRESS = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0" as `0x${string}`;

function loadSimpleAccountAddresses(
  filePath: string,
  limit: number
): `0x${string}`[] {
  const raw = fs.readFileSync(filePath, "utf8");
  const parsed = JSON.parse(raw);

  return parsed.slice(0, limit).map((addr: unknown, i: number) => {
    if (typeof addr !== "string" || !/^0x[a-fA-F0-9]{40}$/.test(addr)) {
      throw new Error(`Invalid address at index ${i}: ${addr}`);
    }

    return addr as `0x${string}`;
  });
}

// -----------------------------
// Precompute accounts + calldata once
// -----------------------------
async function prepareAccounts(publicClient: any) {
  return await Promise.all(
    SIMPLE_ACCOUNT_ADDRESSES.map((addr, i) => {

      const ownerIndex = Math.floor(i / SCAS_PER_OWNER);
      const ownerKey = SIMPLE_ACCOUNT_OWNER_KEYS[ownerIndex]!;

      const owner = privateKeyToAccount(ownerKey);
      
      return toSimpleSmartAccount({
        owner,
        client: publicClient,
        entryPoint: ENTRYPOINT,
        address: addr,
      });
    })
  );
}

function prepareCalldata() {
  return SIMPLE_ACCOUNT_ADDRESSES.map((_, i) =>
    encodeFunctionData({
      abi: TestTokenAbi,
      functionName: "transfer",
      args: [SIMPLE_ACCOUNT_ADDRESSES[SCA_NUMBER - 1 - i], 1n], // send 1 token
    })
  );
}

// Small sleep helper
function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// -----------------------------
// Run one round (two-step: send, then wait)
// -----------------------------
async function runRound(
  round: number,
  bundlerClient: any,
  simpleAccounts: any[],
  calldatas: string[],
  confirmedBlocks: Set<bigint>
) {
  console.log(`\n================ ROUND ${round} START ================`);

  // Step 1: send all user operations (throttled burst)
  const sendPromises: Promise<{ i: number; userOpHash: string | null }>[] = [];

  for (let i = 0; i < simpleAccounts.length; i++) {
    const account = simpleAccounts[i];
    const calldata = calldatas[i];

    // create the send promise
    const promise = (async () => {
      try {
        const userOpHash = await bundlerClient.sendUserOperation({
          account,
          calls: [{ to: ERC20_ADDRESS, value: 0n, data: calldata }],
          callGasLimit: 300_000n,
          verificationGasLimit: 150_000n,
          preVerificationGas: 150_000n,
          maxPriorityFeePerGas: 10n,
          maxFeePerGas: 30n,
        });

        console.log(
          `[Round ${round}] UserOperation #${i + 1} sent → hash: ${userOpHash}`
        );
        return { i, userOpHash };
      } catch (error) {
        console.error(
          `[Round ${round}] UserOperation #${i + 1} failed to send:`,
          error
        );
        return { i, userOpHash: null };
      }
    })();

    sendPromises.push(promise);

    // throttle: wait 100ms between sends
    await sleep(THROTTLE_TIME);
  }

  const sentOps = await Promise.all(sendPromises);

  // Step 2: wait for confirmations in parallel
  const waitPromises = sentOps.map(async ({ i, userOpHash }) => {
    if (!userOpHash) return null;

    try {
      const receipt = await bundlerClient.waitForUserOperationReceipt({
        hash: userOpHash,
      });

      confirmedBlocks.add(receipt.receipt.blockNumber);

      console.log(
        `[Round ${round}] UserOperation #${i + 1} confirmed in block ${receipt.receipt.blockNumber}!`
      );
      return receipt;
    } catch (error) {
      console.error(
        `[Round ${round}] UserOperation #${i + 1} failed to confirm:`,
        error
      );
      return null;
    }
  });

  const receipts = await Promise.all(waitPromises);

  console.log(`\n================ ROUND ${round} COMPLETE ================`);
  receipts.forEach((r, i) => {
    if (r) {
      console.log(
        `[Round ${round}] #${i + 1}: confirmed in block ${r.receipt.blockNumber}`
      );
    } else {
      console.log(`[Round ${round}] #${i + 1}: failed`);
    }
  });
}

async function dumpConfirmedBlocks(
  publicClient: any,
  confirmedBlocks: Set<bigint>
) {
  const blockNumbers = [...confirmedBlocks].sort((a, b) =>
    a < b ? -1 : a > b ? 1 : 0
  );

  const blocks = await Promise.all(
    blockNumbers.map((blockNumber) =>
      publicClient.getBlock({ blockNumber })
    )
  );

  const lines = [
    "block_number,timestamp,timestamp_iso",
    ...blocks.map((block) => {
      const timestampSeconds = block.timestamp;
      const timestampIso = new Date(
        Number(timestampSeconds) * 1000
      ).toISOString();

      return `${block.number},${timestampSeconds},${timestampIso}`;
    }),
  ];

  fs.writeFileSync(
    CONFIRMED_BLOCKS_LOG_FILE,
    `${lines.join("\n")}\n`,
    "utf8"
  );

  console.log(
    `Logged ${blocks.length} confirmed blocks to ${CONFIRMED_BLOCKS_LOG_FILE}`
  );
}

// -----------------------------
// Main
// -----------------------------
async function main() {
  // Public client
  const publicClient = createPublicClient({
    chain: {
      id: 1337,
      name: "anvil",
      nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 },
      rpcUrls: { default: { http: [CHAIN_RPC] } },
    },
    transport: http(CHAIN_RPC),
  });

  // Bundler client
  const bundlerClient = createBundlerClient({
    client: publicClient,
    transport: http(BUNDLER_RPC),
  });

  // Prepare reusable objects once
  const simpleAccounts = await prepareAccounts(publicClient);
  const calldatas = prepareCalldata();

  // Unique blocks containing at least one confirmed UserOperation.
  const confirmedBlocks = new Set<bigint>();

  // Run N rounds sequentially
  for (let round = 1; round <= ROUNDS_TOTAL; round++) {
    await runRound(round, bundlerClient, simpleAccounts, calldatas, confirmedBlocks);
  }

  // Perform block lookups and disk I/O only after the workload finishes.
  await dumpConfirmedBlocks(publicClient, confirmedBlocks);

  console.log("\n=== All rounds finished ===");
  process.exit(0);
}

// Run
main().catch(console.error);
