import { useState, useRef } from "react";
import { Zap, Loader2, Volume2, ShoppingCart, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { useX402Pay } from "@/hooks/useX402Pay";
import { useSuiWallet } from "@/hooks/useSuiWallet";
import { BACKEND_CONFIG } from "@/lib/api";

interface PayPerUseButtonProps {
  voiceId: string;
  modelUri: string;
  creatorAddress: string;
  voiceName: string;
  /** Price in SUI per session (default 0.1) */
  priceSui?: number;
  /** Uses unlocked per payment (default 2) */
  usesPerPayment?: number;
  /** Called after user buys full license */
  onUpgradeToBuy?: () => void;
}

export function PayPerUseButton({
  voiceId,
  modelUri,
  creatorAddress,
  voiceName,
  priceSui = 0.1,
  usesPerPayment = 2,
  onUpgradeToBuy,
}: PayPerUseButtonProps) {
  const { isConnected, address } = useSuiWallet();
  const { pay, isPaying } = useX402Pay();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [passId, setPassId] = useState<string | null>(null);
  const [usesLeft, setUsesLeft] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleOpen = () => {
    setOpen(true);
    setAudioUrl(null);
    setError(null);
  };

  const generate = async (currentPassId: string) => {
    if (!text.trim() || !address) return;
    setIsGenerating(true);
    setError(null);

    try {
      const resp = await fetch(`${BACKEND_CONFIG.BASE_URL}/api/tts/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          modelUri,
          text: text.trim(),
          requesterAccount: address,
          voiceObjectId: voiceId,
          passId: currentPassId,
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.message || err.error || "Generation failed");
      }

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePayAndGenerate = async () => {
    if (!text.trim()) {
      setError("Enter some text first");
      return;
    }

    setError(null);

    // If we already have a pass with uses left, just generate
    if (passId && usesLeft && usesLeft > 0) {
      await generate(passId);
      setUsesLeft((u) => (u !== null ? u - 1 : null));
      return;
    }

    // Pay and get a new UsagePass
    const result = await pay({
      voiceId,
      creatorAddress,
      priceSui,
      uses: usesPerPayment,
    });

    if (!result) return;

    setPassId(result.passId ?? null);
    setUsesLeft(result.usesRemaining);

    await generate(result.passId ?? "");
    setUsesLeft((u) => (u !== null ? u - 1 : null));
  };

  const hasActivePass = passId && usesLeft !== null && usesLeft > 0;

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="border-primary/40 text-primary hover:bg-primary/10 gap-1.5"
        onClick={handleOpen}
      >
        <Zap className="h-3.5 w-3.5" />
        Try · {priceSui} SUI
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              Pay-Per-Use · {voiceName}
            </DialogTitle>
            <DialogDescription>
              {hasActivePass ? (
                <span className="text-green-500 font-medium">
                  {usesLeft} use{usesLeft !== 1 ? "s" : ""} remaining
                </span>
              ) : (
                `Pay ${priceSui} SUI for ${usesPerPayment} voice generations`
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            <Textarea
              placeholder="Enter text to speak…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={3}
              className="resize-none"
            />

            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {error}
              </div>
            )}

            {audioUrl && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Volume2 className="h-4 w-4" />
                  Generated audio
                </div>
                <audio
                  ref={audioRef}
                  src={audioUrl}
                  controls
                  autoPlay
                  className="w-full h-10"
                />
              </div>
            )}

            <div className="flex flex-col gap-2">
              <Button
                onClick={handlePayAndGenerate}
                disabled={isPaying || isGenerating || !text.trim() || !isConnected}
                className="w-full"
              >
                {isPaying ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Approving payment…
                  </>
                ) : isGenerating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating audio…
                  </>
                ) : hasActivePass ? (
                  <>
                    <Volume2 className="mr-2 h-4 w-4" />
                    Generate ({usesLeft} left)
                  </>
                ) : (
                  <>
                    <Zap className="mr-2 h-4 w-4" />
                    Pay {priceSui} SUI &amp; Generate
                  </>
                )}
              </Button>

              {/* Upsell after uses exhausted */}
              {passId && usesLeft === 0 && (
                <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-center space-y-2">
                  <p className="text-sm font-medium">
                    Used all {usesPerPayment} generations!
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Buy the full license for unlimited access.
                  </p>
                  <div className="flex gap-2 justify-center">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handlePayAndGenerate}
                    >
                      <Zap className="mr-1 h-3.5 w-3.5" />
                      Pay for more
                    </Button>
                    {onUpgradeToBuy && (
                      <Button
                        size="sm"
                        onClick={() => {
                          setOpen(false);
                          onUpgradeToBuy();
                        }}
                      >
                        <ShoppingCart className="mr-1 h-3.5 w-3.5" />
                        Buy License
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {!isConnected && (
                <p className="text-xs text-center text-muted-foreground">
                  Connect your wallet to pay
                </p>
              )}

              <div className="flex items-center justify-center gap-3 pt-1">
                <Badge variant="outline" className="text-xs">
                  <Zap className="mr-1 h-3 w-3" />
                  Sui Testnet
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {usesPerPayment} uses · 24 h expiry · no subscription
                </span>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
