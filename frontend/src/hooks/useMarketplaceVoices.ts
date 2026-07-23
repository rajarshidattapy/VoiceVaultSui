import { useCallback, useEffect, useState } from "react";
import { useSuiClient } from "@mysten/dapp-kit";
import { CONTRACTS } from "@/lib/contracts";
import { fetchBlobRef, fetchManifestFromUri, getPreviewUrl, isWalrusUri } from "@/lib/walrus";
import { parseVoiceObject, VOICE_TYPE, VoiceMetadata } from "./useVoiceMetadata";
import { VoiceWithWalrusMetadata } from "./useVoicesWithWalrusMetadata";

const TX_PAGE_LIMIT = 50;
const MAX_TX_PAGES = 6;
const OBJECT_BATCH_SIZE = 50;

function getAddressOwner(owner: unknown): string | null {
  if (!owner || typeof owner !== "object") {
    return null;
  }

  const value = owner as Record<string, any>;
  return typeof value.AddressOwner === "string" ? value.AddressOwner : null;
}

function chunk<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    chunks.push(items.slice(i, i + size));
  }
  return chunks;
}

async function fetchVoicesByObjectId(suiClient: any, objectIds: string[]): Promise<VoiceMetadata[]> {
  const voices: VoiceMetadata[] = [];

  for (const ids of chunk(objectIds, OBJECT_BATCH_SIZE)) {
    const objects = await suiClient.multiGetObjects({
      ids,
      options: { showContent: true, showOwner: true, showType: true },
    });

    for (const obj of objects) {
      if (obj.error) {
        continue;
      }

      const voice = parseVoiceObject(obj);
      if (voice) {
        voices.push(voice);
      }
    }
  }

  return voices;
}

async function fetchVoicesByOwner(suiClient: any, owners: string[]): Promise<VoiceMetadata[]> {
  const results = await Promise.all(
    owners.map(async (owner) => {
      try {
        const objects = await suiClient.getOwnedObjects({
          owner,
          filter: { StructType: VOICE_TYPE },
          options: { showContent: true, showOwner: true, showType: true },
        });

        return (objects.data ?? [])
          .map((obj: any) => parseVoiceObject(obj))
          .filter((voice: VoiceMetadata | null): voice is VoiceMetadata => voice !== null);
      } catch (err) {
        console.warn(`Failed to fetch voices for owner ${owner}:`, err);
        return [];
      }
    })
  );

  return results.flat();
}

async function discoverMarketplaceVoices(suiClient: any): Promise<VoiceMetadata[]> {
  const objectIds: string[] = [];
  const objectOrder = new Map<string, number>();
  const ownerOrder = new Map<string, number>();
  let orderIndex = 0;
  let cursor: string | null | undefined = null;

  const rememberObject = (objectId: string, order: number) => {
    if (!objectOrder.has(objectId)) {
      objectOrder.set(objectId, order);
      objectIds.push(objectId);
    }
  };

  const rememberOwner = (owner: string | null, order: number) => {
    if (owner && !ownerOrder.has(owner)) {
      ownerOrder.set(owner, order);
    }
  };

  for (let pageIndex = 0; pageIndex < MAX_TX_PAGES; pageIndex += 1) {
    const page = await suiClient.queryTransactionBlocks({
      filter: {
        MoveFunction: {
          package: CONTRACTS.PACKAGE_ID,
          module: CONTRACTS.VOICE_IDENTITY.module,
          function: "register_voice",
        },
      },
      options: { showInput: true, showObjectChanges: true },
      order: "descending",
      limit: TX_PAGE_LIMIT,
      cursor,
    });

    for (const tx of page.data ?? []) {
      const txOrder = orderIndex;
      orderIndex += 1;

      for (const change of tx.objectChanges ?? []) {
        const objectChange = change as any;
        if (objectChange.objectType !== VOICE_TYPE || !objectChange.objectId) {
          continue;
        }

        if (objectChange.type !== "deleted" && objectChange.type !== "wrapped") {
          rememberObject(objectChange.objectId, txOrder);
          rememberOwner(getAddressOwner(objectChange.owner) || getAddressOwner(objectChange.recipient), txOrder);
        }
      }

      rememberOwner((tx as any).transaction?.data?.sender ?? null, txOrder);
    }

    if (!page.hasNextPage || !page.nextCursor) {
      break;
    }

    cursor = page.nextCursor;
  }

  const voicesById = new Map<string, VoiceMetadata>();
  const voiceOrder = new Map<string, number>();

  const addVoice = (voice: VoiceMetadata, fallbackOrder: number) => {
    if (voicesById.has(voice.objectId)) {
      return;
    }

    voicesById.set(voice.objectId, voice);
    voiceOrder.set(voice.objectId, objectOrder.get(voice.objectId) ?? fallbackOrder);
  };

  const objectVoices = await fetchVoicesByObjectId(suiClient, objectIds);
  objectVoices.forEach((voice) => addVoice(voice, Number.MAX_SAFE_INTEGER));

  const ownerEntries = Array.from(ownerOrder.entries());
  const ownerVoices = await fetchVoicesByOwner(
    suiClient,
    ownerEntries.map(([owner]) => owner)
  );
  ownerVoices.forEach((voice) => {
    addVoice(voice, ownerOrder.get(voice.owner) ?? Number.MAX_SAFE_INTEGER);
  });

  return Array.from(voicesById.values()).sort(
    (a, b) => (voiceOrder.get(a.objectId) ?? Number.MAX_SAFE_INTEGER) - (voiceOrder.get(b.objectId) ?? Number.MAX_SAFE_INTEGER)
  );
}

async function enrichVoiceWithWalrus(
  voice: VoiceMetadata,
  objectUrls: string[]
): Promise<VoiceWithWalrusMetadata> {
  if (!isWalrusUri(voice.modelUri)) {
    return { ...voice, storageProtocol: "unknown" };
  }

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
    };
  } catch (err) {
    console.warn(`Failed to fetch Walrus metadata for ${voice.modelUri}:`, err);
    return { ...voice, storageProtocol: "walrus" };
  }
}

export function useMarketplaceVoices() {
  const suiClient = useSuiClient();
  const [voices, setVoices] = useState<VoiceWithWalrusMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState(0);

  const refetch = useCallback(() => {
    setRefreshToken((value) => value + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const objectUrls: string[] = [];

    const loadVoices = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const discoveredVoices = await discoverMarketplaceVoices(suiClient);
        const enrichedVoices = await Promise.all(
          discoveredVoices.map((voice) => enrichVoiceWithWalrus(voice, objectUrls))
        );

        if (!cancelled) {
          setVoices(enrichedVoices);
        }
      } catch (err: any) {
        console.error("Failed to discover marketplace voices:", err);
        if (!cancelled) {
          setError(err.message || "Failed to discover marketplace voices");
          setVoices([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadVoices();

    return () => {
      cancelled = true;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [suiClient, refreshToken]);

  return { voices, isLoading, error, refetch };
}
