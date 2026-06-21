import { useState, useEffect } from "react";
import { useSuiClient } from "@mysten/dapp-kit";
import { CONTRACTS, mistToSui } from "@/lib/contracts";
import { parseMoveString } from "@/lib/moveUtils";
import type { SuiJsonRpcClient } from "@mysten/sui/jsonRpc";

export interface VoiceMetadata {
  owner: string;
  voiceId: string;
  objectId: string; // Sui object ID
  name: string;
  modelUri: string;
  rights: string;
  pricePerUse: number; // in SUI
  createdAt: number;
}

export const VOICE_TYPE = `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::VoiceIdentity`;

/**
 * Parse a VoiceIdentity object's fields into VoiceMetadata
 */
export function parseVoiceObject(obj: any): VoiceMetadata | null {
  try {
    const content = obj.data?.content;
    if (!content || content.dataType !== "moveObject") return null;

    const fields = content.fields as any;
    return {
      owner: fields.owner as string,
      objectId: obj.data.objectId,
      voiceId: fields.voice_id?.toString() || obj.data.objectId,
      name: parseMoveString(fields.name),
      modelUri: parseMoveString(fields.model_uri),
      rights: parseMoveString(fields.rights),
      pricePerUse: mistToSui(Number(fields.price_per_use || 0)),
      createdAt: Number(fields.created_at || 0),
    };
  } catch {
    return null;
  }
}

/**
 * Fetch voice metadata for a specific owner address by querying owned objects
 */
export function useVoiceMetadata(ownerAddress: string | null) {
  const suiClient = useSuiClient();
  const [metadata, setMetadata] = useState<VoiceMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ownerAddress) {
      setMetadata(null);
      return;
    }

    const fetchMetadata = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const result = await suiClient.getOwnedObjects({
          owner: ownerAddress,
          filter: { StructType: VOICE_TYPE },
          options: { showContent: true },
        });

        if (!result.data || result.data.length === 0) {
          setMetadata(null);
          setError(null);
          return;
        }

        // Take the first VoiceIdentity object
        const voice = parseVoiceObject(result.data[0]);
        setMetadata(voice);
      } catch (err: any) {
        if (!err.message?.includes("not found")) {
          console.error("Error fetching voice metadata:", err);
        }
        setError(null);
        setMetadata(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMetadata();
  }, [ownerAddress, suiClient]);

  return { metadata, isLoading, error };
}

/**
 * Fetch voice ID for a specific owner (standalone function)
 */
export async function getVoiceId(suiClient: SuiJsonRpcClient, ownerAddress: string): Promise<string | null> {
  try {
    const result = await suiClient.getOwnedObjects({
      owner: ownerAddress,
      filter: { StructType: VOICE_TYPE },
      options: { showContent: true },
    });

    if (!result.data || result.data.length === 0) return null;

    const voice = parseVoiceObject(result.data[0]);
    return voice?.voiceId || null;
  } catch (error) {
    console.error("Error fetching voice ID:", error);
    return null;
  }
}

/**
 * Check if a voice exists for an owner address (standalone function)
 */
export async function checkVoiceExists(suiClient: SuiJsonRpcClient, ownerAddress: string): Promise<boolean> {
  try {
    const result = await suiClient.getOwnedObjects({
      owner: ownerAddress,
      filter: { StructType: VOICE_TYPE },
    });

    return (result.data?.length || 0) > 0;
  } catch (error) {
    console.error("Error checking voice existence:", error);
    return false;
  }
}
