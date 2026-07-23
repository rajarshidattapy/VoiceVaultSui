export type { MurfVoiceParams as ChatterboxParams } from "./murfVoice";
export {
  murfVoiceClone as chatterboxVoiceClone,
  murfTTS as chatterboxTTS,
} from "./murfVoice";

export function getChatterboxErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string" && error.trim()) return error;
  return "Murf TTS failed. Please try again.";
}
