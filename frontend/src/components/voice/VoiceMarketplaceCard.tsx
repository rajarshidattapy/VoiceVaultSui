import { useState, useEffect } from "react";
import { VoiceMetadata } from "@/hooks/useVoiceMetadata";
import { VoiceWithWalrusMetadata } from "@/hooks/useVoicesWithWalrusMetadata";
import { usePayForInference } from "@/hooks/usePayForInference";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ShoppingCart, Coins, Play } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { formatAddress } from "@/lib/sui";
import { isWalrusUri } from "@/lib/walrus";
import { isVoicePurchased } from "@/lib/purchasedVoices";
import { PayPerUseButton } from "@/components/x402/PayPerUseButton";

interface VoiceMarketplaceCardProps {
  voice: VoiceWithWalrusMetadata;
  onPaymentSuccess?: (txHash: string, voice: VoiceMetadata) => void;
}

export function VoiceMarketplaceCard({ voice, onPaymentSuccess }: VoiceMarketplaceCardProps) {
  const { payForInference, getPaymentBreakdown, isPaying } = usePayForInference();
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [breakdown, setBreakdown] = useState<{
    total: number;
    platformFee: number;
    royalty: number;
    creator: number;
  } | null>(null);

  const price = voice.pricePerUse;
  const isPurchased = isVoicePurchased(voice.voiceId, voice.owner);
  const isWalrus = isWalrusUri(voice.modelUri);
  const isLegacyWalrus = voice.modelUri.startsWith("walrus://");
  
  // Fetch breakdown from backend when dialog opens, fallback to local calculation
  useEffect(() => {
    if (showPaymentDialog && !breakdown) {
      const fetchBreakdown = async () => {
        try {
          const { backendApi } = await import("@/lib/api");
          const result = await backendApi.getPaymentBreakdown(price);
          setBreakdown({
            total: result.totalAmount,
            platformFee: result.breakdown.platformFee.amount,
            royalty: result.breakdown.royalty.amount,
            creator: result.breakdown.creator.amount,
          });
        } catch (err) {
          console.error("Failed to fetch breakdown from backend, using local calculation:", err);
          // Fallback to local calculation
          const localBreakdown = getPaymentBreakdown(price);
          setBreakdown(localBreakdown);
        }
      };
      fetchBreakdown();
    } else if (!showPaymentDialog) {
      // Reset when dialog closes
      setBreakdown(null);
    }
  }, [showPaymentDialog, price]);
  
  // Ensure we have a breakdown to display (use local as default)
  const displayBreakdown = breakdown || getPaymentBreakdown(price);

  const handlePurchase = async () => {
    setShowPaymentDialog(false);

    const result = await payForInference({
      voiceId: voice.objectId,       // VoiceIdentity object ID → minted into LicensePass
      creatorAddress: voice.owner,
      amount: price,
      royaltyRecipient: voice.owner,
      onSuccess: (txHash) => {
        if (onPaymentSuccess) {
          onPaymentSuccess(txHash, voice);
        }
      },
    });

    if (result?.success) {
      // Payment successful - trigger voice generation in parent component
    }
  };

  return (
    <>
      <Card className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>{voice.name}</span>
            <div className="flex items-center gap-2">
              {isWalrus && (
                <Badge variant="outline" className="text-xs">
                  Walrus
                </Badge>
              )}
              {isLegacyWalrus && (
                <Badge variant="outline" className="text-xs">
                  Legacy Walrus
                </Badge>
              )}
              {isPurchased && (
                <Badge variant="default" className="text-xs bg-green-600">
                  Purchased
                </Badge>
              )}
              <Badge variant="secondary">
                {price.toFixed(4)} SUI
              </Badge>
            </div>
          </CardTitle>
          <CardDescription>
            {voice.description || `by ${formatAddress(voice.owner)}`}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {voice.previewAudioUrl && (
            <div className="space-y-2">
              <span className="text-xs text-muted-foreground">Preview:</span>
              <audio 
                src={voice.previewAudioUrl} 
                controls 
                className="w-full h-8"
                preload="metadata"
              />
            </div>
          )}
          <div className="text-sm space-y-1">
            <div>
              <span className="text-muted-foreground">Rights:</span>{" "}
              <span className="font-medium">{voice.rights}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Creator:</span>{" "}
              <span className="font-mono text-xs">{formatAddress(voice.owner)}</span>
            </div>
            {isWalrus && (
              <div>
                <span className="text-muted-foreground">Storage:</span>{" "}
                <span className="text-xs text-green-600">Walrus (Content-Addressed)</span>
              </div>
            )}
            {isLegacyWalrus && (
              <div>
                <span className="text-muted-foreground">Storage:</span>{" "}
                <span className="text-xs text-amber-600">Walrus (Legacy)</span>
              </div>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          {isPurchased ? (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => { window.location.href = "/upload"; }}
            >
              <Play className="mr-2 h-4 w-4" />
              Use in Upload Page
            </Button>
          ) : (
            <div className="flex w-full gap-2">
              {/* Pay-per-use: try before buying */}
              <PayPerUseButton
                voiceId={voice.objectId}
                modelUri={voice.modelUri}
                creatorAddress={voice.owner}
                voiceName={voice.name}
                priceSui={0.1}
                usesPerPayment={2}
                onUpgradeToBuy={() => setShowPaymentDialog(true)}
              />

              {/* Full license purchase */}
              <Button
                onClick={() => setShowPaymentDialog(true)}
                disabled={isPaying}
                className="flex-1"
              >
                {isPaying ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <ShoppingCart className="mr-2 h-4 w-4" />
                    Buy Voice
                  </>
                )}
              </Button>
            </div>
          )}
        </CardFooter>
      </Card>

      {/* Payment Confirmation Dialog */}
      <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Payment</DialogTitle>
            <DialogDescription>
              Review the payment breakdown before proceeding
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Voice:</span>
              <span className="font-medium">{voice.name}</span>
            </div>

            <div className="border-t pt-4 space-y-2">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Total Amount:</span>
                <span className="font-medium">{displayBreakdown.total.toFixed(4)} SUI</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Platform Fee (2.5%):</span>
                <span>{displayBreakdown.platformFee.toFixed(4)} SUI</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Royalty (10%):</span>
                <span>{displayBreakdown.royalty.toFixed(4)} SUI</span>
              </div>
              <div className="flex justify-between items-center text-sm font-medium border-t pt-2">
                <span>Creator Receives:</span>
                <span className="text-primary">{displayBreakdown.creator.toFixed(4)} SUI</span>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPaymentDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handlePurchase} disabled={isPaying}>
              {isPaying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Coins className="mr-2 h-4 w-4" />
                  Confirm Payment
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
