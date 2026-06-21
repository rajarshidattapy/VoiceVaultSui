import { backendApi } from "@/lib/api";

export interface MurfVoiceParams {
  voiceId?: string;
}

export async function murfTTS(text: string, params: MurfVoiceParams = {}): Promise<Blob> {
  return backendApi.generateTTS("murf://default", text, undefined, undefined, undefined, undefined, params.voiceId);
}

export async function murfVoiceClone(
  text: string,
  _audioFile: File | Blob,
  params: MurfVoiceParams = {}
): Promise<Blob> {
  return murfTTS(text, params);
}
