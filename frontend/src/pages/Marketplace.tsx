import { useState, useEffect } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, SlidersHorizontal, TrendingUp, Clock, Star, RefreshCw } from "lucide-react";
import { Helmet } from "react-helmet-async";
import { VoiceMetadata } from "@/hooks/useVoiceMetadata";
import { VoiceMarketplaceCard } from "@/components/voice/VoiceMarketplaceCard";
import { toast } from "sonner";
import { useMarketplaceVoices } from "@/hooks/useMarketplaceVoices";
import { useSuiWallet } from "@/hooks/useSuiWallet";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { InfoIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

const filterTabs = [
  { id: "trending", label: "Trending", icon: TrendingUp },
  { id: "newest", label: "Newest", icon: Clock },
  { id: "top-rated", label: "Top Rated", icon: Star },
];

const Marketplace = () => {
  const { address } = useSuiWallet();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("trending");

  const { voices, isLoading, error, refetch } = useMarketplaceVoices();

  const handlePurchaseSuccess = async (
    voice: VoiceMetadata,
    txHash: string,
    metadata?: { mintsLicensePass: boolean }
  ) => {
    // Track purchased voice in localStorage
    const { addPurchasedVoice } = await import("@/lib/purchasedVoices");
    addPurchasedVoice({
      voiceId: voice.voiceId,
      objectId: voice.objectId,
      name: voice.name,
      modelUri: voice.modelUri,
      owner: voice.owner,
      price: voice.pricePerUse,
      buyer: address || undefined,
      licenseMode: metadata?.mintsLicensePass ? "onchain" : "legacy_tx",
      purchasedAt: Date.now(),
      txHash: txHash,
    });

    toast.success("Voice purchased successfully!", {
      description: "You can now use this voice in the Upload page for TTS generation.",
      duration: 5000,
      action: {
        label: "Go to Upload",
        onClick: () => {
          window.location.href = "/upload";
        },
      },
    });
  };

  return (
    <>
      <Helmet>
        <title>Voice Marketplace - VoiceVault</title>
        <meta name="description" content="Discover and license AI voice models from creators worldwide. Find the perfect voice for your project." />
      </Helmet>
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-32 pb-16">
          <div className="container mx-auto px-4">
            {/* Header */}
            <div className="max-w-2xl mb-8">
              <h1 className="font-display text-4xl md:text-5xl font-bold mb-4">
                Voice <span className="gradient-text">Marketplace</span>
              </h1>
              <p className="text-lg text-muted-foreground">
                Discover unique AI voice models registered on Sui blockchain. License instantly, pay per use.
              </p>
              <div className="flex items-center gap-2 mt-2">
                <p className="text-sm text-muted-foreground">
                  Showing <strong>{voices.length}</strong> voice{voices.length !== 1 ? 's' : ''} registered on-chain
                </p>
                {voices.length > 0 && (
                  <span className="text-xs text-muted-foreground">
                    • All voices verified on Sui blockchain
                  </span>
                )}
              </div>
            </div>



            {/* Search and Filters */}
            <div className="flex flex-col md:flex-row gap-4 mb-8">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  placeholder="Search voices by name or creator address..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-12 h-12 bg-card border-border"
                />
              </div>
              <Button
                variant="outline"
                className="h-12"
                onClick={() => {
                  refetch();
                  toast.info("Refreshing voices from Sui blockchain...");
                }}
                disabled={isLoading}
              >
                <RefreshCw className={`h-5 w-5 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button variant="outline" className="h-12">
                <SlidersHorizontal className="h-5 w-5 mr-2" />
                Filters
              </Button>
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
              {filterTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveFilter(tab.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${
                    activeFilter === tab.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  <tab.icon className="h-4 w-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {error && (
              <Alert className="mb-8">
                <InfoIcon className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Voice Grid */}
            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-64 w-full" />
                ))}
              </div>
            ) : voices.length === 0 ? (
              <Alert>
                <InfoIcon className="h-4 w-4" />
                <AlertDescription>
                  <strong>No voices registered on-chain yet.</strong>
                  <br />
                  <span className="text-sm mt-2 block">
                    Be the first to register your voice on Sui blockchain!
                  </span>
                  <span className="text-xs text-muted-foreground mt-2 block">
                    Go to the Upload page to register your voice on-chain and make it available in the marketplace.
                  </span>
                </AlertDescription>
              </Alert>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {voices
                  .filter((voice) =>
                    searchQuery
                      ? voice.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        voice.owner.toLowerCase().includes(searchQuery.toLowerCase())
                      : true
                  )
                  .map((voice) => (
                    <VoiceMarketplaceCard
                      key={`${voice.owner}-${voice.voiceId}`}
                      voice={voice}
                      onPaymentSuccess={(txHash, voice, metadata) => handlePurchaseSuccess(voice, txHash, metadata)}
                    />
                  ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </>
  );
};

export default Marketplace;
