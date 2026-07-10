import { createPublicClient, http, encodeFunctionData, parseEther } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { toSimpleSmartAccount } from "permissionless/accounts";
import { createBundlerClient } from "viem/account-abstraction";
import TestTokenAbi from "./TestToken.abi.json" with { type: "json" };

// -----------------------------
// Configuration
// -----------------------------
const CHAIN_RPC = "http://127.0.0.1:8545";     // Anvil
const BUNDLER_RPC = "http://127.0.0.1:3000";   // Alto bundler

const ENTRYPOINT = {
  address: "0x5FbDB2315678afecb367f032d93F642f64180aa3" as `0x${string}`,
  version: "0.7" as const
};

// This is the sender Smart Account
const SIMPLE_ACCOUNT_ADDRESS = "0xe3e63CA4413073Ce2F0B2c10a239fa2c0627d585" as `0x${string}`;

// This is the key of the EOA that deployed the Smart Account
const SIMPLE_ACCOUNT_OWNER_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";

// This is the token contract
const ERC20_ADDRESS = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0" as `0x${string}`;

// This is the recipient Smart Account
const RECIPIENT = "0xb2500dd50B9D3157110bb7832DE9570a17bcAAfd" as `0x${string}`;

// Main sends tokens from sender SCA to recipient SCA
// To be able to do that, first:
// - Fund SCAs with Ether to pay the transactions
// - Fund SCAs with ERC20 tokens to do the transfers

// -----------------------------
// Main
// -----------------------------
async function main() {
  // Owner account
  const owner = privateKeyToAccount(SIMPLE_ACCOUNT_OWNER_KEY);

  // Public client
  const publicClient = createPublicClient({
    chain: {
      id: 1337,
      name: "anvil",
      nativeCurrency: { name: "ETH", symbol: "ETH", decimals: 18 },
      rpcUrls: { default: { http: [CHAIN_RPC] } }
    },
    transport: http(CHAIN_RPC)
  });

  // Bundler client
  const bundlerClient = createBundlerClient({
    client: publicClient,
    transport: http(BUNDLER_RPC),
  });

  // Wrap manually deployed SimpleAccount
  const simpleAccount = await toSimpleSmartAccount({
    owner,
    client: publicClient,
    entryPoint: ENTRYPOINT,
    address: SIMPLE_ACCOUNT_ADDRESS
  });

  console.log("SimpleAccount address:", simpleAccount.address);

  // const nonce = await simpleAccount.getNonce();
  // console.log("Current nonce:", nonce.toString());

  // Build ERC20.transfer calldata
  const transferCalldata = encodeFunctionData({
    abi: TestTokenAbi,
    functionName: "transfer",
    args: [RECIPIENT, 1]
  });


  const numberOfSends = 10;

  for (let i = 0; i < numberOfSends; i++) {
    try {
      console.log(`Sending UserOperation #${i + 1}...`);
      
      // max fields are required to avoid gas fee bumping by bundler
      const userOpHash = await bundlerClient.sendUserOperation({
        account: simpleAccount,
        calls: [{ to: ERC20_ADDRESS, value: BigInt(0), data: transferCalldata }],
        callGasLimit: 300_000n,
        verificationGasLimit: 150_000n,
        preVerificationGas: 150_000n,
        maxPriorityFeePerGas: 10n,
        maxFeePerGas: 30n
      });

      console.log(`UserOperation hash for #${i + 1}: ${userOpHash}`);

      // Wait for the transaction to be included in a block
      console.log(`Waiting for UserOperation #${i + 1} to be confirmed...`);
      const receipt = await bundlerClient.waitForUserOperationReceipt({ hash: userOpHash });

      //console.log("Transaction receipt:", receipt);
      console.log(`Transaction for #${i + 1} confirmed in block ${receipt.receipt.blockNumber}!`);

    } catch (error) {
      console.error(`Failed to send or confirm UserOperation #${i + 1}:`, error);
      // You can add logic here to exit the loop or retry the failed transaction
      break; 
    }
  }

  // console.log("Batch sending completed.");

  // Send UserOperation via bundler client
  // const userOpHash = await bundlerClient.sendUserOperation({
  //   account: simpleAccount,
  //   calls: [{ to: ERC20_ADDRESS, value: BigInt(0), data: transferCalldata }],
  //   callGasLimit: 300_000n,        // gas for the ERC-20 transfer
  //   verificationGasLimit: 150_000n, // gas for validateUserOp
  //   preVerificationGas: 150_000n    // gas for bundler overhead
  //   // nonce: 1n
  // });

  // console.log("UserOperation hash:", userOpHash);

  // // Optional: wait for inclusion
  // const receipt = await bundlerClient.waitForUserOperationReceipt({ hash: userOpHash });
  // console.log("Transaction receipt:", receipt);
}



// Run
main().catch(console.error);
