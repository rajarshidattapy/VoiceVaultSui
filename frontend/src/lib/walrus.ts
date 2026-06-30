export interface WalrusBlobRef {
  blobId?: string;
  objectId?: string;
  size?: number;
  chunked?: boolean;
  blobIds?: string[];
  objectIds?: string[];
}

export interface VoiceManifest {
  voiceId: string;
  owner: string;
  blobs: Record<string, WalrusBlobRef>;
  walrusUri?: string;
  manifestBlobId?: string;
  manifestObjectId?: string;
  previewUrl?: string | null;
  version?: number;
}

const getBackendBaseUrl = () => {
  return import.meta.env.VITE_PROXY_URL || import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
};

const AGGREGATOR_URL =
  import.meta.env.VITE_WALRUS_AGGREGATOR_URL?.replace(/\/$/, "") ||
  `${getBackendBaseUrl()}/api/walrus`;

export function parseWalrusUri(uri: string): string {
  if (!uri.startsWith("walrus://")) {
    throw new Error(`Invalid Walrus URI: ${uri}`);
  }
  return uri.slice("walrus://".length);
}

export function buildWalrusUri(blobId: string): string {
  return `walrus://${blobId}`;
}

export function isWalrusUri(uri: string): boolean {
  return uri.startsWith("walrus://");
}

export function getBlobUrl(blobId: string): string {
  if (AGGREGATOR_URL.includes("/api/walrus") || AGGREGATOR_URL.endsWith("/v1")) {
    return `${AGGREGATOR_URL}/blobs/${encodeURIComponent(blobId)}`;
  }

  return `${AGGREGATOR_URL}/v1/blobs/${encodeURIComponent(blobId)}`;
}

export async function fetchBlob(blobId: string): Promise<ArrayBuffer> {
  const response = await fetch(getBlobUrl(blobId));
  if (!response.ok) {
    throw new Error(`Blob fetch failed: ${response.status}`);
  }
  return response.arrayBuffer();
}

export async function fetchManifest(manifestBlobId: string): Promise<VoiceManifest> {
  const manifestBuffer = await fetchBlob(manifestBlobId);
  const manifest = JSON.parse(new TextDecoder().decode(manifestBuffer)) as VoiceManifest;
  if (!manifest.walrusUri) {
    manifest.walrusUri = buildWalrusUri(manifestBlobId);
  }
  return manifest;
}

export async function fetchManifestFromUri(uri: string): Promise<VoiceManifest> {
  return fetchManifest(parseWalrusUri(uri));
}

function concatArrayBuffers(chunks: ArrayBuffer[]): ArrayBuffer {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
  const result = new Uint8Array(totalLength);

  let offset = 0;
  for (const chunk of chunks) {
    result.set(new Uint8Array(chunk), offset);
    offset += chunk.byteLength;
  }

  return result.buffer;
}

export async function fetchBlobRef(blobRef: WalrusBlobRef): Promise<ArrayBuffer> {
  if (blobRef.chunked) {
    const blobIds = blobRef.blobIds || [];
    const chunks = await Promise.all(blobIds.map((blobId) => fetchBlob(blobId)));
    return concatArrayBuffers(chunks);
  }

  if (!blobRef.blobId) {
    throw new Error("Blob reference does not contain a blobId");
  }

  return fetchBlob(blobRef.blobId);
}

export async function fetchWalrusFile(uri: string, filename: string): Promise<ArrayBuffer> {
  const manifest = await fetchManifestFromUri(uri);
  const blobRef = manifest.blobs[filename];

  if (!blobRef) {
    throw new Error(`'${filename}' not found in manifest`);
  }

  return fetchBlobRef(blobRef);
}

export function getWalrusFileUrl(manifest: VoiceManifest, filename: string): string | null {
  const blobRef = manifest.blobs[filename];
  if (!blobRef || blobRef.chunked || !blobRef.blobId) {
    return null;
  }
  return getBlobUrl(blobRef.blobId);
}

export function getPreviewUrl(manifest: VoiceManifest): string | null {
  return getWalrusFileUrl(manifest, "preview.wav");
}
