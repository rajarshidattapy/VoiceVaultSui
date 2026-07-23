import { Transaction } from "@mysten/sui/transactions";
import { CONTRACTS } from "./contracts";

function isTxContextParameter(param: unknown): boolean {
  if (!param || typeof param !== "object") {
    return false;
  }

  const value = param as Record<string, any>;
  if (value.MutableReference) {
    return isTxContextParameter(value.MutableReference);
  }
  if (value.Reference) {
    return isTxContextParameter(value.Reference);
  }

  const struct = value.Struct;
  return (
    !!struct &&
    struct.address === "0x2" &&
    struct.module === "tx_context" &&
    struct.name === "TxContext"
  );
}

async function getPaymentParameterCount(suiClient: any): Promise<number> {
  const normalized = await suiClient.getNormalizedMoveFunction({
    package: CONTRACTS.PACKAGE_ID,
    module: CONTRACTS.PAYMENT.module,
    function: "pay_with_royalty_split",
  });

  return (normalized.parameters ?? []).filter((param: unknown) => !isTxContextParameter(param)).length;
}

export async function buildRoyaltyPaymentArguments(
  suiClient: any,
  tx: Transaction,
  data: {
    paymentCoin: any;
    voiceId: string;
    creatorAddress: string;
    royaltyRecipient?: string;
  }
): Promise<{ args: any[]; mintsLicensePass: boolean }> {
  const parameterCount = await getPaymentParameterCount(suiClient);
  const recipient = data.royaltyRecipient || data.creatorAddress;

  if (parameterCount === 5) {
    return {
      mintsLicensePass: true,
      args: [
        data.paymentCoin,
        tx.pure.address(data.voiceId),
        tx.pure.address(data.creatorAddress),
        tx.pure.address(CONTRACTS.PLATFORM_ADDRESS),
        tx.pure.address(recipient),
      ],
    };
  }

  if (parameterCount === 4) {
    return {
      mintsLicensePass: false,
      args: [
        data.paymentCoin,
        tx.pure.address(data.creatorAddress),
        tx.pure.address(CONTRACTS.PLATFORM_ADDRESS),
        tx.pure.address(recipient),
      ],
    };
  }

  throw new Error(`Unsupported payment contract arity: ${parameterCount}`);
}
