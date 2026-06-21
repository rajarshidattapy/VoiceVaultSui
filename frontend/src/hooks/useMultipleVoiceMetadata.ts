import { useState, useEffect } from "react";
import { useSuiClient } from "@mysten/dapp-kit";
import { CONTRACTS, mistToSui } from "@/lib/contracts";
import { VoiceMetadata } from "./useVoiceMetadata";
import { parseMoveString } from "@/lib/moveUtils";

const VOICE_TYPE = `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::VoiceIdentity`;

/**
 * Fetch metadata for multiple voice addresses in parallel
 */
export function useMultipleVoiceMetadata(addresses: string[]) {
  const suiClient = useSuiClient();
  const [voices, setVoices] = useState<VoiceMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!addresses || addresses.length === 0) {
      setVoices([]);
      setIsLoading(false);
      return;
    }

    const fetchAllMetadata = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const promises = addresses.map(async (address) => {
          try {
            const result = await suiClient.getOwnedObjects({
              owner: address,
              filter: { StructType: VOICE_TYPE },
              options: { showContent: true },
            });

            if (!result.data || result.data.length === 0) return null;

            const obj = result.data[0];
            const content = obj.data?.content;
            if (!content || content.dataType !== "moveObject") return null;

            const fields = content.fields as any;
            return {
              owner: fields.owner as string,
              objectId: obj.data!.objectId,
              voiceId: fields.voice_id?.toString() || obj.data!.objectId,
              name: parseMoveString(fields.name),
              modelUri: parseMoveString(fields.model_uri),
              rights: parseMoveString(fields.rights),
              pricePerUse: mistToSui(Number(fields.price_per_use || 0)),
              createdAt: Number(fields.created_at || 0),
            } as VoiceMetadata;
          } catch (err) {
            console.warn(`Failed to fetch metadata for ${address}:`, err);
            return null;
          }
        });

        const results = await Promise.all(promises);
        const validVoices = results.filter((v): v is VoiceMetadata => v !== null);
        setVoices(validVoices);
      } catch (err: any) {
        console.error("Error fetching multiple voice metadata:", err);
        setError(err.message || "Failed to fetch voices");
        setVoices([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllMetadata();
  }, [addresses.join(","), suiClient]);

  return { voices, isLoading, error };
}
