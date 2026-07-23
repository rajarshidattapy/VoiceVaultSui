const getBackendUrl = () => {
  const envUrl = import.meta.env.VITE_PROXY_URL || import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL;
  return envUrl || "http://localhost:8000";
};

async function readError(response: Response, fallbackMessage: string): Promise<never> {
  const errorText = await response.text();
  let errorData: { error?: string; message?: string };

  try {
    errorData = JSON.parse(errorText);
  } catch {
    errorData = { error: errorText || fallbackMessage };
  }

  throw new Error(errorData.error || errorData.message || fallbackMessage);
}

export const BACKEND_CONFIG = {
  get BASE_URL() {
    return getBackendUrl();
  },
  ENDPOINTS: {
    UNIFIED_TTS: "/api/tts/generate",
    PAYMENT_BREAKDOWN: "/api/payment/breakdown",
    VOICE_PROCESS: "/api/voice/process",
    WALRUS_UPLOAD: "/api/walrus/upload",
    WALRUS_DOWNLOAD: "/api/walrus/download",
    WALRUS_DELETE: "/api/walrus/delete",
    TTS_CLONE: "/api/tts/clone",
  },
};

export const backendApi = {
  async generateTTS(
    modelUri: string,
    text: string,
    requesterAccount?: string,
    voiceObjectId?: string,
    purchaseTxHash?: string,
    creatorAddress?: string,
  ): Promise<Blob> {
    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.UNIFIED_TTS}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        modelUri,
        text,
        ...(requesterAccount ? { requesterAccount } : {}),
        ...(voiceObjectId ? { voiceObjectId } : {}),
        ...(purchaseTxHash ? { purchaseTxHash } : {}),
        ...(creatorAddress ? { creatorAddress } : {}),
      }),
    });

    if (!response.ok) {
      await readError(response, "TTS generation failed");
    }

    return response.blob();
  },

  async cloneTTS(audioFile: File | Blob, text: string): Promise<Blob> {
    const formData = new FormData();
    formData.append("audio", audioFile, "reference.wav");
    formData.append("text", text);

    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.TTS_CLONE}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      await readError(response, "Voice cloning failed");
    }

    return response.blob();
  },

  async getPaymentBreakdown(amount: number) {
    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.PAYMENT_BREAKDOWN}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount }),
    });

    if (!response.ok) {
      await readError(response, "Failed to calculate payment breakdown");
    }

    return response.json();
  },

  async processVoiceModel(
    audioFile: File,
    name: string,
    owner: string,
    voiceId: string,
    description?: string,
  ) {
    const formData = new FormData();
    formData.append("audio", audioFile);
    formData.append("name", name);
    formData.append("owner", owner);
    formData.append("voiceId", voiceId);
    if (description) {
      formData.append("description", description);
    }

    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.VOICE_PROCESS}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      await readError(response, "Voice processing failed");
    }

    return response.json();
  },

  async uploadToWalrus(
    accountOrUri: string,
    voiceIdOrAccount: string,
    bundleFiles: {
      embedding: Blob;
      config: Blob;
      meta: Blob;
      preview?: Blob;
    },
  ) {
    const formData = new FormData();
    formData.append("embedding.bin", bundleFiles.embedding, "embedding.bin");
    formData.append("config.json", bundleFiles.config, "config.json");
    formData.append("meta.json", bundleFiles.meta, "meta.json");
    if (bundleFiles.preview) {
      formData.append("preview.wav", bundleFiles.preview, "preview.wav");
    }

    const headers: Record<string, string> = {};
    if (accountOrUri.startsWith("walrus://")) {
      headers["X-Walrus-Uri"] = accountOrUri;
      headers["X-Sui-Account"] = voiceIdOrAccount;
    } else {
      headers["X-Sui-Account"] = accountOrUri;
      headers["X-Voice-Id"] = voiceIdOrAccount;
    }

    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.WALRUS_UPLOAD}`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      await readError(response, "Walrus upload failed");
    }

    return response.json();
  },

  async downloadFromWalrus(
    uri: string,
    filename: string,
    requesterAccount?: string,
    voiceObjectId?: string,
    purchaseTxHash?: string,
    creatorAddress?: string
  ): Promise<ArrayBuffer> {
    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.WALRUS_DOWNLOAD}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uri, filename, requesterAccount, voiceObjectId, purchaseTxHash, creatorAddress }),
    });

    if (!response.ok) {
      await readError(response, "Walrus download failed");
    }

    return response.arrayBuffer();
  },

  async deleteFromWalrus(uri: string, account: string) {
    const response = await fetch(`${BACKEND_CONFIG.BASE_URL}${BACKEND_CONFIG.ENDPOINTS.WALRUS_DELETE}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ uri, account }),
    });

    if (!response.ok) {
      await readError(response, "Walrus delete failed");
    }

    return response.json();
  },

  async downloadModelFile(
    uri: string,
    filename: string,
    requesterAccount?: string,
    voiceObjectId?: string,
    purchaseTxHash?: string,
    creatorAddress?: string
  ): Promise<ArrayBuffer> {
    if (uri.startsWith("walrus://")) {
      return backendApi.downloadFromWalrus(uri, filename, requesterAccount, voiceObjectId, purchaseTxHash, creatorAddress);
    }
    throw new Error(`Unsupported model URI format: ${uri}`);
  },

  async deleteModelBundle(uri: string, account: string) {
    if (uri.startsWith("walrus://")) {
      return backendApi.deleteFromWalrus(uri, account);
    }
    throw new Error(`Unsupported model URI format: ${uri}`);
  },
};
