import { Transaction } from "@mysten/sui/transactions";
import { CONTRACTS } from "./contracts";

export const VOICE_IDENTITY_TYPE = `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::VoiceIdentity`;
const VOICE_REGISTRY_TYPE = `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::VoiceRegistry`;

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

async function getExplicitParameterCount(
  suiClient: any,
  functionName: "register_voice" | "delete_voice"
): Promise<number> {
  const normalized = await suiClient.getNormalizedMoveFunction({
    package: CONTRACTS.PACKAGE_ID,
    module: CONTRACTS.VOICE_IDENTITY.module,
    function: functionName,
  });

  return (normalized.parameters ?? []).filter((param: unknown) => !isTxContextParameter(param)).length;
}

async function usesRegistryArgument(
  suiClient: any,
  functionName: "register_voice" | "delete_voice",
  parameterCountWithRegistry: number
): Promise<boolean> {
  const explicitParameterCount = await getExplicitParameterCount(suiClient, functionName);
  return explicitParameterCount >= parameterCountWithRegistry;
}

async function assertRegistryObject(suiClient: any) {
  if (!CONTRACTS.VOICE_REGISTRY_ID || CONTRACTS.VOICE_REGISTRY_ID === "0x") {
    throw new Error("Voice registry object ID is not configured in VITE_SUI_VOICE_REGISTRY_ID.");
  }

  const registry = await suiClient.getObject({
    id: CONTRACTS.VOICE_REGISTRY_ID,
    options: { showType: true, showOwner: true },
  });

  if (registry.error) {
    throw new Error(`Voice registry object could not be loaded: ${registry.error.code}`);
  }

  if (registry.data?.type === "package") {
    throw new Error("VITE_SUI_VOICE_REGISTRY_ID points to a package ID, not a VoiceRegistry object.");
  }

  if (registry.data?.type !== VOICE_REGISTRY_TYPE) {
    throw new Error("VITE_SUI_VOICE_REGISTRY_ID does not point to the configured package's VoiceRegistry.");
  }
}

function getAddressOwner(owner: unknown): string | null {
  if (!owner || typeof owner !== "object") {
    return null;
  }

  const value = owner as Record<string, any>;
  return typeof value.AddressOwner === "string" ? value.AddressOwner : null;
}

export async function assertOwnedVoiceObject(
  suiClient: any,
  voiceObjectId: string,
  walletAddress: string
) {
  const voice = await suiClient.getObject({
    id: voiceObjectId,
    options: { showOwner: true, showType: true },
  });

  if (voice.error) {
    throw new Error(`Voice object could not be loaded: ${voice.error.code}`);
  }

  if (voice.data?.type !== VOICE_IDENTITY_TYPE) {
    throw new Error("The selected object is not a VoiceIdentity from the configured package.");
  }

  const owner = getAddressOwner(voice.data.owner);
  if (!owner || owner.toLowerCase() !== walletAddress.toLowerCase()) {
    throw new Error("The selected voice is not owned by the connected wallet.");
  }
}

export async function buildRegisterVoiceArguments(
  suiClient: any,
  tx: Transaction,
  data: {
    name: string;
    modelUri: string;
    rights: string;
    priceInMist: number;
  }
) {
  const args = [
    tx.pure.string(data.name),
    tx.pure.string(data.modelUri),
    tx.pure.string(data.rights),
    tx.pure.u64(data.priceInMist),
  ];

  if (await usesRegistryArgument(suiClient, "register_voice", 5)) {
    await assertRegistryObject(suiClient);
    return [tx.object(CONTRACTS.VOICE_REGISTRY_ID), ...args];
  }

  return args;
}

export async function buildDeleteVoiceArguments(
  suiClient: any,
  tx: Transaction,
  voiceObjectId: string
) {
  if (await usesRegistryArgument(suiClient, "delete_voice", 2)) {
    await assertRegistryObject(suiClient);
    return [tx.object(CONTRACTS.VOICE_REGISTRY_ID), tx.object(voiceObjectId)];
  }

  return [tx.object(voiceObjectId)];
}
