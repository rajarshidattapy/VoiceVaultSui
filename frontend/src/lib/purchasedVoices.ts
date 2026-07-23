// Track purchased voices in localStorage

export interface PurchasedVoice {
  voiceId: string;
  objectId?: string;
  name: string;
  modelUri: string;
  owner: string;
  buyer?: string;
  licenseMode?: "onchain" | "legacy_tx";
  price: number;
  purchasedAt: number;
  txHash: string;
}

const STORAGE_KEY = "voicevault_purchased_voices";
export const PURCHASED_VOICES_EVENT = "voicevault:purchased-voices-changed";

function notifyPurchasedVoicesChanged(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(PURCHASED_VOICES_EVENT));
  }
}

/**
 * Get all purchased voices for the current user
 */
export function getPurchasedVoices(walletAddress?: string): PurchasedVoice[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];

    const allPurchases: PurchasedVoice[] = JSON.parse(stored);

    if (walletAddress) {
      const normalizedWallet = walletAddress.toLowerCase();
      return allPurchases.filter((voice) => !voice.buyer || voice.buyer.toLowerCase() === normalizedWallet);
    }

    return allPurchases;
  } catch (error) {
    console.error("Error reading purchased voices:", error);
    return [];
  }
}

/**
 * Add a purchased voice
 */
export function addPurchasedVoice(voice: PurchasedVoice): void {
  try {
    const existing = getPurchasedVoices();
    const purchase = {
      ...voice,
      buyer: voice.buyer?.toLowerCase(),
    };
    
    // Check if already purchased
    const voiceObjectId = purchase.objectId || purchase.voiceId;
    const alreadyPurchased = existing.some((v) => {
      const existingObjectId = v.objectId || v.voiceId;
      return (
        existingObjectId === voiceObjectId &&
        v.owner.toLowerCase() === purchase.owner.toLowerCase() &&
        v.buyer?.toLowerCase() === purchase.buyer
      );
    });

    if (alreadyPurchased) {
      console.log("Voice already purchased");
      notifyPurchasedVoicesChanged();
      return;
    }

    existing.push(purchase);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(existing));
    notifyPurchasedVoicesChanged();
    console.log("[PurchasedVoices] Added:", voice.name);
  } catch (error) {
    console.error("Error adding purchased voice:", error);
  }
}

/**
 * Check if a voice has been purchased
 */
export function isVoicePurchased(voiceObjectId: string, owner: string, walletAddress?: string): boolean {
  const purchased = getPurchasedVoices(walletAddress);
  return purchased.some(
    (v) => (v.objectId || v.voiceId) === voiceObjectId && v.owner.toLowerCase() === owner.toLowerCase()
  );
}

/**
 * Get purchased voices that use OpenAI models
 */
export function getPurchasedOpenAIVoices(): PurchasedVoice[] {
  const purchased = getPurchasedVoices();
  return purchased.filter((v) => v.modelUri.startsWith("openai:"));
}

/**
 * Remove a purchased voice by voiceId and owner
 */
export function removePurchasedVoice(voiceId: string, owner: string): void {
  try {
    const existing = getPurchasedVoices();
    const filtered = existing.filter(
      (v) => !((v.objectId || v.voiceId) === voiceId && v.owner === owner)
    );
    
    if (filtered.length < existing.length) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
      notifyPurchasedVoicesChanged();
      console.log("[PurchasedVoices] Removed:", voiceId);
    }
  } catch (error) {
    console.error("Error removing purchased voice:", error);
  }
}

/**
 * Remove a purchased voice by modelUri
 */
export function removePurchasedVoiceByUri(modelUri: string): void {
  try {
    const existing = getPurchasedVoices();
    const filtered = existing.filter((v) => v.modelUri !== modelUri);
    
    if (filtered.length < existing.length) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
      notifyPurchasedVoicesChanged();
      console.log("[PurchasedVoices] Removed voice with URI:", modelUri);
    }
  } catch (error) {
    console.error("Error removing purchased voice by URI:", error);
  }
}

/**
 * Clear all purchased voices (for testing)
 */
export function clearPurchasedVoices(): void {
  localStorage.removeItem(STORAGE_KEY);
  notifyPurchasedVoicesChanged();
  console.log("[PurchasedVoices] Cleared all");
}
