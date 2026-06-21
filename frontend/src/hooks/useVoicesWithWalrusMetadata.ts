import { useEffect, useState } from "react";
import { useSuiClient } from "@mysten/dapp-kit";
import { CONTRACTS, mistToSui } from "@/lib/contracts";
import { VoiceMetadata } from "./useVoiceMetadata";
import { fetchBlobRef, fetchManifestFromUri, getPreviewUrl, isWalrusUri } from "@/lib/walrus";
import { parseMoveString } from "@/lib/moveUtils";

const VOICE_TYPE = `${CONTRACTS.PACKAGE_ID}::${CONTRACTS.VOICE_IDENTITY.module}::VoiceIdentity`;

export interface VoiceWithWalrusMetadata extends VoiceMetadata {
  description?: string;
  previewAudioUrl?: string;
  storageProtocol?: "walrus" | "unknown";
}

export function useVoicesWithWalrusMetadata(addresses: string[]) {
  const suiClient = useSuiClient();
  const [voices, setVoices] = useState<VoiceWithWalrusMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!addresses || addresses.length === 0) {
      setVoices([]);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    const objectUrls: string[] = [];

    const fetchAllVoices = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const onChainPromises = addresses.map(async (address) => {
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
            console.warn(`Failed to fetch on-chain metadata for ${address}:`, err);
            return null;
          }
        });

        const onChainResults = await Promise.all(onChainPromises);
        const validOnChainVoices = onChainResults.filter((voice): voice is VoiceMetadata => voice !== null);

        const enrichedPromises = validOnChainVoices.map(async (voice) => {
          if (isWalrusUri(voice.modelUri)) {
            try {
              const manifest = await fetchManifestFromUri(voice.modelUri);

              let walrusMeta: Record<string, any> = {};
              const metaRef = manifest.blobs["meta.json"];
              if (metaRef) {
                const metaBuffer = await fetchBlobRef(metaRef);
                walrusMeta = JSON.parse(new TextDecoder().decode(metaBuffer));
              }

              let previewAudioUrl = getPreviewUrl(manifest) || undefined;
              if (!previewAudioUrl && manifest.blobs["preview.wav"]) {
                try {
                  const previewBuffer = await fetchBlobRef(manifest.blobs["preview.wav"]);
                  const previewBlob = new Blob([previewBuffer], { type: "audio/wav" });
                  previewAudioUrl = URL.createObjectURL(previewBlob);
                  objectUrls.push(previewAudioUrl);
                } catch {
                  console.debug(`Preview not available for ${voice.modelUri}`);
                }
              }

              return {
                ...voice,
                name: walrusMeta.name || voice.name,
                description: walrusMeta.description,
                previewAudioUrl,
                storageProtocol: "walrus",
              } as VoiceWithWalrusMetadata;
            } catch (err) {
              console.warn(`Failed to fetch Walrus metadata for ${voice.modelUri}:`, err);
              return {
                ...voice,
                storageProtocol: "walrus",
              } as VoiceWithWalrusMetadata;
            }
          }

          if (voice.modelUri.startsWith("walrus://")) {
            try {
              const { backendApi } = await import("@/lib/api");

              const metaBuffer = await backendApi.downloadFromWalrus(voice.modelUri, "meta.json");
              const metaText = new TextDecoder().decode(metaBuffer);
              const walrusMeta = JSON.parse(metaText);

              let previewAudioUrl: string | undefined;
              try {
                const previewBuffer = await backendApi.downloadFromWalrus(voice.modelUri, "preview.wav");
                const previewBlob = new Blob([previewBuffer], { type: "audio/wav" });
                previewAudioUrl = URL.createObjectURL(previewBlob);
                objectUrls.push(previewAudioUrl);
              } catch {
                console.debug(`Preview not available for ${voice.modelUri}`);
              }

              return {
                ...voice,
                name: walrusMeta.name || voice.name,
                description: walrusMeta.description,
                previewAudioUrl,
                storageProtocol: "walrus",
              } as VoiceWithWalrusMetadata;
            } catch (err) {
              console.warn(`Failed to fetch Walrus metadata for ${voice.modelUri}:`, err);
              return {
                ...voice,
                storageProtocol: "walrus",
              } as VoiceWithWalrusMetadata;
            }
          }

          return {
            ...voice,
            storageProtocol: "unknown",
          } as VoiceWithWalrusMetadata;
        });

        const enrichedVoices = await Promise.all(enrichedPromises);
        if (!cancelled) {
          setVoices(enrichedVoices);
        }
      } catch (err: any) {
        console.error("Error fetching voices with Walrus metadata:", err);
        if (!cancelled) {
          setError(err.message || "Failed to fetch voices");
          setVoices([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchAllVoices();

    return () => {
      cancelled = true;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [addresses.join(","), suiClient]);

  return { voices, isLoading, error };
}
