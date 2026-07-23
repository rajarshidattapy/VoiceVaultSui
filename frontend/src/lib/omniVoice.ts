import { Client } from "@gradio/client";

export interface OmniVoiceParams {
  lang?: string;
  refText?: string;
  instruct?: string;
  inferenceSteps?: number;
  guidanceScale?: number;
  denoise?: boolean;
  speed?: number;
  duration?: number;
  preprocessPrompt?: boolean;
  postprocessOutput?: boolean;
  gender?: string;
  age?: string;
  pitch?: string;
  style?: string;
  englishAccent?: string;
  chineseDialect?: string;
}

const DEFAULT_OMNI_SPACE = "k2-fsa/OmniVoice";
const OMNI_CLONE_ENDPOINT = "/_clone_fn";
const OMNI_DESIGN_ENDPOINT = "/_design_fn";

const DEFAULT_PARAMS: OmniVoiceParams = {
  lang: "Auto",
  refText: "",
  instruct: "",
  inferenceSteps: 32,
  guidanceScale: 2,
  denoise: true,
  speed: 1,
  preprocessPrompt: true,
  postprocessOutput: true,
  gender: "Auto",
  age: "Auto",
  pitch: "Auto",
  style: "Auto",
  englishAccent: "Auto",
  chineseDialect: "Auto",
};

const VALID_ENGLISH_INSTRUCTS = new Set([
  "american accent",
  "australian accent",
  "british accent",
  "canadian accent",
  "child",
  "chinese accent",
  "elderly",
  "female",
  "high pitch",
  "indian accent",
  "japanese accent",
  "korean accent",
  "low pitch",
  "male",
  "middle-aged",
  "moderate pitch",
  "portuguese accent",
  "russian accent",
  "teenager",
  "very high pitch",
  "very low pitch",
  "whisper",
  "young adult",
]);

function getOmniVoiceSpace(): string {
  return import.meta.env.VITE_OMNI_VOICE_SPACE?.trim() || DEFAULT_OMNI_SPACE;
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function extractErrorText(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error && error.message) return error.message;
  if (!error || typeof error !== "object") return "";

  const record = error as Record<string, unknown>;
  return [record.title, record.message, record.original_msg]
    .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    .join(": ");
}

function isMetadataLoadError(errorText: string): boolean {
  const normalized = errorText.toLowerCase();
  return normalized.includes("metadata could not be loaded") || normalized.includes("status of 401");
}

function isGpuCapacityError(errorText: string): boolean {
  const normalized = errorText.toLowerCase();
  return normalized.includes("zerogpu") || normalized.includes("no gpu was available");
}

function resolveDuration(text: string, duration?: number): number {
  if (typeof duration === "number" && Number.isFinite(duration) && duration > 0) {
    return duration;
  }

  const words = text.trim().split(/\s+/).filter(Boolean).length;
  const estimatedSeconds = Math.ceil(words / 2.4) + 1;
  return Math.min(30, Math.max(3, estimatedSeconds || 3));
}

function normalizeEnglishInstruct(instruct?: string): string {
  if (!instruct?.trim()) return "";

  return instruct
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => VALID_ENGLISH_INSTRUCTS.has(item))
    .join(", ");
}

export function getOmniVoiceErrorMessage(error: unknown): string {
  const message = stripHtml(extractErrorText(error));

  if (isMetadataLoadError(message)) {
    return "OmniVoice Space metadata could not be loaded. Check VITE_OMNI_VOICE_SPACE and make sure the Hugging Face Space is public.";
  }

  if (isGpuCapacityError(message)) {
    return "The OmniVoice GPU did not become available in time. Your voice purchase is valid, but TTS generation needs GPU capacity. Try again later or use your own GPU-backed OmniVoice Space.";
  }

  return message || "OmniVoice TTS failed. Please try again.";
}

async function audioResultToBlob(data: any): Promise<Blob> {
  const audio = Array.isArray(data) ? data[0] : data;
  const status = Array.isArray(data) && typeof data[1] === "string" ? stripHtml(data[1]) : "";

  if (!audio && status) {
    throw new Error(status);
  }

  if (audio instanceof Blob) return audio;

  if (typeof audio === "string") {
    const res = await fetch(audio);
    if (!res.ok) throw new Error(`Unable to download OmniVoice audio output (${res.status})`);
    return res.blob();
  }

  if (audio?.url) {
    const res = await fetch(audio.url);
    if (!res.ok) throw new Error(`Unable to download OmniVoice audio output (${res.status})`);
    return res.blob();
  }

  if (audio?.data) {
    const res = await fetch(audio.data);
    if (!res.ok) throw new Error(`Unable to read OmniVoice audio output (${res.status})`);
    return res.blob();
  }

  throw new Error(status || "Unexpected audio output format from OmniVoice");
}

async function predictOmniVoice(endpoint: string, payload: Record<string, unknown>): Promise<Blob> {
  try {
    const client = await Client.connect(getOmniVoiceSpace());
    const result = await client.predict(endpoint, payload);
    return audioResultToBlob(result.data);
  } catch (error) {
    throw new Error(getOmniVoiceErrorMessage(error));
  }
}

export async function omniVoiceTTS(text: string, params: OmniVoiceParams = {}): Promise<Blob> {
  const p = { ...DEFAULT_PARAMS, ...params };

  return predictOmniVoice(OMNI_DESIGN_ENDPOINT, {
    text,
    lang: p.lang,
    ns: p.inferenceSteps,
    gs: p.guidanceScale,
    dn: p.denoise,
    sp: p.speed,
    du: resolveDuration(text, p.duration),
    pp: p.preprocessPrompt,
    po: p.postprocessOutput,
    param_9: p.gender,
    param_10: p.age,
    param_11: p.pitch,
    param_12: p.style,
    param_13: p.englishAccent,
    param_14: p.chineseDialect,
  });
}

export async function omniVoiceClone(
  text: string,
  audioFile: File | Blob,
  params: OmniVoiceParams = {}
): Promise<Blob> {
  const p = { ...DEFAULT_PARAMS, ...params };

  return predictOmniVoice(OMNI_CLONE_ENDPOINT, {
    text,
    lang: p.lang,
    ref_aud: audioFile,
    ref_text: p.refText,
    instruct: normalizeEnglishInstruct(p.instruct),
    ns: p.inferenceSteps,
    gs: p.guidanceScale,
    dn: p.denoise,
    sp: p.speed,
    du: resolveDuration(text, p.duration),
    pp: p.preprocessPrompt,
    po: p.postprocessOutput,
  });
}
