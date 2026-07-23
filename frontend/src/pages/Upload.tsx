import { Navbar } from "@/components/layout/Navbar";
import { VoiceRegistrationForm } from "@/components/voice/VoiceRegistrationForm";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Sparkles, Download, Loader2, Mic2, Upload as UploadIcon } from "lucide-react";
import { useState, useRef, useEffect } from "react";
import { Helmet } from "react-helmet-async";
import { toast } from "sonner";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getPurchasedVoices, PURCHASED_VOICES_EVENT, removePurchasedVoiceByUri } from "@/lib/purchasedVoices";
import { useSuiWallet } from "@/hooks/useSuiWallet";
import { useVoiceMetadata } from "@/hooks/useVoiceMetadata";

const getReadableErrorMessage = (error: unknown, fallback: string): string => {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string" && error.trim()) return error;
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) {
      return message.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    }
  }
  return fallback;
};

const Upload = () => {
  // ------------------- TTS with Purchased Voices -------------------
  const [ttsText, setTtsText] = useState("");
  const [selectedPurchasedVoice, setSelectedPurchasedVoice] = useState<string>("");
  const [purchasedVoices, setPurchasedVoices] = useState<Array<{ voiceId: string; objectId?: string; name: string; modelUri: string; owner: string; txHash?: string; isOwned?: boolean }>>([]);
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState<string | null>(null);

  // ------------------- Voice Model Processing (Walrus) -------------------
  const { address, isConnected } = useSuiWallet();
  const { metadata: ownVoiceMetadata } = useVoiceMetadata(address?.toString() || null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [recording, setRecording] = useState(false);
  const [voiceName, setVoiceName] = useState("");
  const [voiceDescription, setVoiceDescription] = useState("");
  const [processingLoading, setProcessingLoading] = useState(false);
  const [processedVoiceUri, setProcessedVoiceUri] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // ------------------- Registration Autofill -------------------
  const [autoName, setAutoName] = useState("");
  const [autoModelUri, setAutoModelUri] = useState("");

  // ------------------- Voice Cloning (Murf) -------------------
  const [cloneRecording, setCloneRecording] = useState(false);
  const [cloneRecordedAudio, setCloneRecordedAudio] = useState<File | null>(null);
  const [cloneText, setCloneText] = useState("");
  const [cloneLoading, setCloneLoading] = useState(false);
  const [cloneOutputAudio, setCloneOutputAudio] = useState<string | null>(null);

  const cloneMediaRecorderRef = useRef<MediaRecorder | null>(null);
  const cloneAudioChunksRef = useRef<Blob[]>([]);

  // ------------------- Load available voices (owned + purchased) -------------------
  useEffect(() => {
    const loadAvailableVoices = async () => {
      try {
        const allVoices: Array<{ voiceId: string; objectId?: string; name: string; modelUri: string; owner: string; txHash?: string; isOwned?: boolean }> = [];

        const checkModelUriExists = async (
          uri: string,
          requesterAccount?: string,
          voiceObjectId?: string,
          purchaseTxHash?: string,
          creatorAddress?: string
        ): Promise<boolean> => {
          if (!uri.startsWith("walrus://")) return true;
          try {
            const { backendApi } = await import("@/lib/api");
            await backendApi.downloadModelFile(uri, "meta.json", requesterAccount, voiceObjectId, purchaseTxHash, creatorAddress);
            return true;
          } catch {
            return false;
          }
        };

        if (ownVoiceMetadata && address) {
          const exists = await checkModelUriExists(ownVoiceMetadata.modelUri, address.toString(), ownVoiceMetadata.objectId);
          if (exists) {
            allVoices.push({
              voiceId: ownVoiceMetadata.voiceId,
              objectId: ownVoiceMetadata.objectId,
              name: ownVoiceMetadata.name,
              modelUri: ownVoiceMetadata.modelUri,
              owner: ownVoiceMetadata.owner,
              isOwned: true,
            });
          }
        }

        const purchased = getPurchasedVoices(address?.toString());
        for (const v of purchased) {
          const voiceObjectId = v.objectId || v.voiceId;
          const exists = await checkModelUriExists(v.modelUri, address?.toString(), voiceObjectId, v.txHash, v.owner);
          if (exists) {
            allVoices.push({ voiceId: v.voiceId, objectId: voiceObjectId, name: v.name, modelUri: v.modelUri, owner: v.owner, txHash: v.txHash, isOwned: false });
          } else {
            removePurchasedVoiceByUri(v.modelUri);
          }
        }

        setPurchasedVoices(allVoices);

        const marketplaceVoices = allVoices.filter(v => !v.isOwned);
        if (selectedPurchasedVoice && !marketplaceVoices.some(v => v.modelUri === selectedPurchasedVoice)) {
          setSelectedPurchasedVoice("");
        }
        if (marketplaceVoices.length > 0 && !selectedPurchasedVoice) {
          setSelectedPurchasedVoice(marketplaceVoices[0].modelUri);
        }
      } catch {
        setPurchasedVoices([]);
      }
    };

    loadAvailableVoices();

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "voicevault_purchased_voices") loadAvailableVoices();
    };
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener(PURCHASED_VOICES_EVENT, loadAvailableVoices);
    const interval = setInterval(loadAvailableVoices, 5000);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener(PURCHASED_VOICES_EVENT, loadAvailableVoices);
      clearInterval(interval);
    };
  }, [ownVoiceMetadata, address, selectedPurchasedVoice]);

  // ------------------- Mic Record (Walrus) -------------------
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => audioChunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        setSelectedFile(new File([blob], "mic.wav", { type: "audio/wav" }));
      };
      recorder.start();
      setRecording(true);
      toast.info("Recording started");
    } catch {
      toast.error("Mic permission denied");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
    toast.info("Recording stopped");
  };

  // ------------------- TTS Generation with Available Voices -------------------
  const handleGenerateTTS = async () => {
    if (!ttsText.trim()) { toast.error("Please enter text to generate"); return; }
    if (!selectedPurchasedVoice) { toast.error("Please select a voice"); return; }
    if (!isConnected || !address) { toast.error("Please connect your wallet to use voices"); return; }

    setTtsLoading(true);
    try {
      const { backendApi } = await import("@/lib/api");
      toast.info("Generating speech via Murf...");
      const selectedVoice = purchasedVoices.find((voice) => voice.modelUri === selectedPurchasedVoice);

      const audioBlob = await backendApi.generateTTS(
        selectedPurchasedVoice,
        ttsText,
        address.toString(),
        selectedVoice?.objectId || selectedVoice?.voiceId,
        selectedVoice?.txHash,
        selectedVoice?.owner
      );
      setTtsAudioUrl(URL.createObjectURL(audioBlob));
      toast.success("Speech generated successfully!");
    } catch (err: any) {
      console.error("TTS error:", err);
      toast.error("TTS generation failed", {
        description: getReadableErrorMessage(err, "Failed to generate speech"),
        duration: 10000,
      });
    } finally {
      setTtsLoading(false);
    }
  };

  // ------------------- File Upload Handler (Walrus) -------------------
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type.startsWith("audio/")) { setSelectedFile(file); toast.success("Audio file selected"); }
      else toast.error("Please select an audio file");
    }
  };

  // ------------------- Clone Card: Recording -------------------
  const startCloneRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      let mimeType = "audio/webm";
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) mimeType = "audio/webm;codecs=opus";
      else if (MediaRecorder.isTypeSupported("audio/mp4")) mimeType = "audio/mp4";

      const recorder = new MediaRecorder(stream, { mimeType });
      cloneMediaRecorderRef.current = recorder;
      cloneAudioChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) cloneAudioChunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(cloneAudioChunksRef.current, { type: mimeType });
        const ext = mimeType.includes("webm") ? "webm" : mimeType.includes("mp4") ? "mp4" : "wav";
        setCloneRecordedAudio(new File([blob], `voice-${Date.now()}.${ext}`, { type: mimeType }));
      };
      recorder.start(100);
      setCloneRecording(true);
      toast.info("Recording started");
    } catch {
      toast.error("Mic permission denied or recording failed");
    }
  };

  const stopCloneRecording = () => {
    if (cloneMediaRecorderRef.current) {
      cloneMediaRecorderRef.current.stop();
      cloneMediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
    }
    setCloneRecording(false);
    toast.success("Recording stopped");
  };

  const handleCloneFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type.startsWith("audio/") || file.name.match(/\.(wav|mp3|webm|ogg|m4a)$/i)) {
        setCloneRecordedAudio(file);
        toast.success("Audio file selected");
      } else {
        toast.error("Please select an audio file");
      }
    }
  };

  // ------------------- Clone Voice & Generate (Murf) -------------------
  const handleCloneAndGenerate = async () => {
    if (!cloneRecordedAudio) { toast.error("Please record or upload a voice sample first"); return; }
    if (!cloneText.trim()) { toast.error("Please enter the text you want your voice to say"); return; }

    setCloneLoading(true);
    try {
      const { murfVoiceClone } = await import("@/lib/murfVoice");
      toast.info("Cloning your voice and generating speech...");
      const audioBlob = await murfVoiceClone(cloneText.trim(), cloneRecordedAudio);
      setCloneOutputAudio(URL.createObjectURL(audioBlob));
      toast.success("Done! Your voice is speaking the text you wrote.");
    } catch (err: any) {
      console.error("Voice clone error:", err);
      toast.error("Voice cloning failed", {
        description: getReadableErrorMessage(err, "Failed to clone voice and generate speech"),
        duration: 10000,
      });
    } finally {
      setCloneLoading(false);
    }
  };

  // ------------------- Process Audio and Upload to Walrus -------------------
  const handleProcessVoice = async () => {
    if (!isConnected || !address) { toast.error("Please connect your wallet first"); return; }
    if (!selectedFile) { toast.error("Please record or upload an audio file first"); return; }
    if (!voiceName.trim()) { toast.error("Please enter a voice name"); return; }

    setProcessingLoading(true);
    try {
      const { backendApi } = await import("@/lib/api");
      const voiceId = `voice_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const account = address.toString();

      toast.info("Processing audio and generating voice model...");
      const processResult = await backendApi.processVoiceModel(
        selectedFile, voiceName.trim(), account, voiceId,
        voiceDescription.trim() || undefined
      );

      const modelUri = processResult.walrusUri || processResult.uri;

      setAutoName(voiceName.trim());
      setAutoModelUri(modelUri);
      setProcessedVoiceUri(modelUri);

      toast.success("Voice model processed and uploaded to Walrus successfully!", {
        description: `URI: ${modelUri}`,
        duration: 5000,
      });
    } catch (err: any) {
      toast.error(err.message || "Failed to process voice model");
    } finally {
      setProcessingLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Helmet><title>Create Voice - VoiceVault</title></Helmet>
      <Navbar />
      <main className="pt-32 pb-16">
        <div className="container max-w-5xl mx-auto px-4 space-y-16">

          {/* ------------------- Text → Speech with Your Voices ------------------- */}
          <Card>
            <CardHeader>
              <CardTitle>Text → Speech with Your Voices</CardTitle>
              <CardDescription>
                Generate speech using your own registered voice or voices you've purchased from the marketplace
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!isConnected && (
                <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    ⚠️ Please connect your wallet to use voices.
                  </p>
                </div>
              )}

              {purchasedVoices.filter((v) => !v.isOwned).length === 0 ? (
                <div className="p-6 border-2 border-dashed rounded-lg text-center space-y-2">
                  <p className="text-sm text-muted-foreground">No marketplace voices available yet.</p>
                  <p className="text-xs text-muted-foreground">
                    Visit the Marketplace to purchase voices, or register your own voice below.
                  </p>
                  <div className="flex gap-2 justify-center mt-4">
                    <Button variant="outline" onClick={() => { window.location.href = "/marketplace"; }}>
                      Go to Marketplace
                    </Button>
                    <Button variant="outline" onClick={() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })}>
                      Register Your Voice
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="purchased-voice">Select Voice</Label>
                    <Select value={selectedPurchasedVoice} onValueChange={setSelectedPurchasedVoice}>
                      <SelectTrigger id="purchased-voice">
                        <SelectValue placeholder="Select a voice" />
                      </SelectTrigger>
                      <SelectContent>
                        {purchasedVoices.filter((voice) => !voice.isOwned).map((voice) => (
                          <SelectItem key={voice.modelUri} value={voice.modelUri}>
                            {voice.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {purchasedVoices.find(v => v.modelUri === selectedPurchasedVoice)?.isOwned && (
                      <p className="text-xs text-muted-foreground">✓ You own this voice - free to use</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="tts-text">Enter Text</Label>
                    <Textarea
                      id="tts-text"
                      value={ttsText}
                      onChange={(e) => setTtsText(e.target.value)}
                      placeholder="Type the text you want to generate as speech..."
                      className="min-h-[100px]"
                    />
                  </div>

                  <Button onClick={handleGenerateTTS} disabled={ttsLoading || !selectedPurchasedVoice || !isConnected} className="w-full">
                    {ttsLoading ? (
                      <><Loader2 className="h-5 w-5 mr-2 animate-spin" />Generating...</>
                    ) : (
                      <><Sparkles className="h-5 w-5 mr-2" />Generate Speech</>
                    )}
                  </Button>

                  {ttsAudioUrl && (
                    <div className="space-y-3 bg-muted/40 p-4 rounded-xl">
                      <audio controls src={ttsAudioUrl} className="w-full" />
                      <Button variant="outline" onClick={() => { const a = document.createElement("a"); a.href = ttsAudioUrl; a.download = `voicevault-tts-${Date.now()}.wav`; a.click(); }} className="w-full">
                        <Download className="h-4 w-4 mr-2" />Download Audio
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* ------------------- Clone Your Voice with Chatterbox ------------------- */}
          <Card>
            <CardHeader>
              <CardTitle>🎤 Clone Your Voice with Chatterbox</CardTitle>
              <CardDescription>
                Record or upload your voice sample, enter the text you want it to say, then click Clone Voice.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Audio Input */}
              <div className="space-y-4">
                <Label>Record or Upload Audio</Label>
                <div className="border-2 border-dashed rounded-lg p-6 text-center space-y-4">
                  <div className="space-y-2">
                    {!cloneRecording ? (
                      <Button onClick={startCloneRecording} className="w-full" disabled={cloneLoading}>
                        <Mic2 className="h-5 w-5 mr-2" />Start Recording
                      </Button>
                    ) : (
                      <Button onClick={stopCloneRecording} className="w-full" variant="destructive">
                        <Mic2 className="h-5 w-5 mr-2" />Stop Recording
                      </Button>
                    )}
                    {cloneRecording && (
                      <div className="flex items-center justify-center space-x-2 text-red-600 dark:text-red-400">
                        <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse" />
                        <span className="text-sm font-medium">Recording...</span>
                      </div>
                    )}
                  </div>

                  <div className="text-sm text-muted-foreground">OR</div>

                  <div>
                    <input type="file" accept="audio/*,.wav,.mp3,.webm,.ogg,.m4a" onChange={handleCloneFileUpload} className="hidden" id="clone-audio-upload" disabled={cloneLoading} />
                    <Button variant="outline" onClick={() => document.getElementById("clone-audio-upload")?.click()} className="w-full" disabled={cloneLoading}>
                      <UploadIcon className="h-5 w-5 mr-2" />Upload Audio File
                    </Button>
                  </div>

                  {cloneRecordedAudio && (
                    <div className="space-y-2 pt-2 border-t">
                      <p className="text-sm text-green-600 dark:text-green-400 font-medium">
                        ✓ {cloneRecordedAudio.name} ({(cloneRecordedAudio.size / 1024).toFixed(1)} KB)
                      </p>
                      <audio controls src={URL.createObjectURL(cloneRecordedAudio)} className="w-full" />
                    </div>
                  )}
                </div>
              </div>

              {/* Text Input */}
              <div className="space-y-2">
                <Label htmlFor="clone-text">Text to Speak</Label>
                <Textarea
                  id="clone-text"
                  value={cloneText}
                  onChange={(e) => setCloneText(e.target.value)}
                  placeholder="Enter the text you want your cloned voice to speak..."
                  className="min-h-[100px]"
                  disabled={cloneLoading}
                />
              </div>

              {/* Clone Button */}
              <Button onClick={handleCloneAndGenerate} disabled={cloneLoading || !cloneRecordedAudio || !cloneText.trim()} className="w-full">
                {cloneLoading ? (
                  <><Loader2 className="h-5 w-5 mr-2 animate-spin" />Cloning Voice...</>
                ) : (
                  <><Sparkles className="h-5 w-5 mr-2" />Clone Voice</>
                )}
              </Button>

              {/* Output */}
              {cloneOutputAudio && (
                <div className="space-y-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4 rounded-lg">
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    ✓ Your voice is speaking the text you wrote
                  </p>
                  <audio controls src={cloneOutputAudio} className="w-full" />
                  <Button variant="outline" size="sm" onClick={() => { const a = document.createElement("a"); a.href = cloneOutputAudio; a.download = `cloned-voice-${Date.now()}.wav`; a.click(); }} className="w-full">
                    <Download className="h-4 w-4 mr-2" />Download Audio
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ------------------- Voice Model Processing (Walrus) ------------------- */}
          <Card>
            <CardHeader>
              <CardTitle>Step 1: Process Your Voice Model</CardTitle>
              <CardDescription>
                Upload audio → Generate voice embedding → Store on Walrus → Register on Sui blockchain
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {!isConnected && (
                <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                  <p className="text-sm text-yellow-800 dark:text-yellow-200">
                    ⚠️ Please connect your wallet to process and register your voice model.
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <Label>Audio Input (Record or Upload)</Label>
                <div className="border-2 border-dashed rounded-lg p-6 text-center space-y-4">
                  {!recording ? (
                    <Button onClick={startRecording} disabled={!isConnected} className="w-full">
                      <Mic2 className="h-5 w-5 mr-2" />Start Recording
                    </Button>
                  ) : (
                    <Button onClick={stopRecording} className="w-full" variant="destructive">
                      ⏹ Stop Recording
                    </Button>
                  )}

                  <div className="text-sm text-muted-foreground">OR</div>

                  <div>
                    <input type="file" accept="audio/*" onChange={handleFileUpload} className="hidden" id="audio-upload" disabled={!isConnected} />
                    <Button variant="outline" onClick={() => document.getElementById("audio-upload")?.click()} className="w-full" disabled={!isConnected}>
                      <UploadIcon className="h-5 w-5 mr-2" />Upload Audio File
                    </Button>
                  </div>

                  {selectedFile && (
                    <div className="mt-4 p-3 bg-muted/40 rounded-lg">
                      <p className="text-sm font-medium text-primary">
                        ✓ {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">Supported formats: MP3, WAV, Opus</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="voice-name">Voice Name <span className="text-red-500">*</span></Label>
                <Input
                  id="voice-name"
                  placeholder="e.g., My Professional Voice"
                  value={voiceName}
                  onChange={(e) => setVoiceName(e.target.value)}
                  disabled={!isConnected}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="voice-description">Voice Description (Optional)</Label>
                <Textarea
                  id="voice-description"
                  placeholder="Describe your voice model..."
                  value={voiceDescription}
                  onChange={(e) => setVoiceDescription(e.target.value)}
                  className="min-h-[80px]"
                  disabled={!isConnected}
                />
              </div>

              <Button onClick={handleProcessVoice} disabled={processingLoading || !selectedFile || !voiceName.trim() || !isConnected} className="w-full">
                {processingLoading ? (
                  <><Loader2 className="h-5 w-5 mr-2 animate-spin" />Processing & Uploading...</>
                ) : (
                  <><Sparkles className="h-5 w-5 mr-2" />Process Voice & Upload to Walrus</>
                )}
              </Button>

              {processedVoiceUri && (
                <div className="space-y-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4 rounded-lg">
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    ✓ Voice model processed and uploaded to Walrus successfully!
                  </p>
                  <p className="text-xs text-green-700 dark:text-green-300 break-all">Walrus URI: {processedVoiceUri}</p>
                  <p className="text-xs text-muted-foreground mt-2">
                    The Model URI has been auto-filled in the registration form below.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* ------------------- Registration Form ------------------- */}
          <Card>
            <CardHeader>
              <CardTitle>Step 2: Register Your Voice Model on Sui Blockchain</CardTitle>
              <CardDescription>
                After processing and uploading your voice model to Walrus, register it on Sui blockchain to make it available in the marketplace.
                <br />
                {autoModelUri && (
                  <span className="text-sm text-primary mt-2 block">
                    ✓ Model URI auto-filled: <code className="text-xs bg-muted px-1 py-0.5 rounded">{autoModelUri}</code>
                  </span>
                )}
                {!autoModelUri && (
                  <span className="text-sm text-muted-foreground mt-2 block">
                    Complete Step 1 above to process your voice model and get a Walrus URI.
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <VoiceRegistrationForm autoName={autoName} autoModelUri={autoModelUri} />
            </CardContent>
          </Card>

        </div>
      </main>
    </div>
  );
};

export default Upload;
