import { Navbar } from "@/components/layout/Navbar";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { UsageChart } from "@/components/dashboard/UsageChart";
import { Button } from "@/components/ui/button";
import { DollarSign, Mic, Users, Clock, Plus, Settings, ExternalLink, Wallet, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useEffect, useState } from "react";
import { useSuiWallet, getAccountBalance } from "@/hooks/useSuiWallet";
import { useSuiClient } from "@mysten/dapp-kit";
import { useVoicesWithWalrusMetadata } from "@/hooks/useVoicesWithWalrusMetadata";

const recentActivity = [
  { type: "payout", voice: "All Voices", user: "You", amount: 0, time: "Just now" },
];

const Dashboard = () => {
  const { address, isConnected } = useSuiWallet();
  const suiClient = useSuiClient();
  const walletAddress = address || "";
  const connected = isConnected;
  const [suiBalance, setSuiBalance] = useState<number | null>(null);

  const { voices, isLoading: isVoicesLoading } = useVoicesWithWalrusMetadata(walletAddress ? [walletAddress] : []);

  useEffect(() => {
    let cancelled = false;

    async function fetchBalance() {
      if (!walletAddress) {
        setSuiBalance(null);
        return;
      }
      try {
        const balance = await getAccountBalance(suiClient, walletAddress);
        if (!cancelled) {
          setSuiBalance(balance);
        }
      } catch {
        if (!cancelled) {
          setSuiBalance(null);
        }
      }
    }

    fetchBalance();

    return () => {
      cancelled = true;
    };
  }, [walletAddress, suiClient]);

  return (
    <>
      <Helmet>
        <title>Creator Dashboard - VoiceVault</title>
        <meta name="description" content="Manage your AI voice models, track earnings, and monitor usage statistics." />
      </Helmet>
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-32 pb-16">
          <div className="container mx-auto px-4">
            {/* Wallet Connection Alert */}
            {!connected && (
              <Alert className="mb-6 border-primary/50 bg-primary/10">
                <Wallet className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between">
                  <span>Connect your wallet to access all dashboard features</span>
                </AlertDescription>
              </Alert>
            )}

            {connected && walletAddress && (
              <div className="glass-card p-4 mb-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Wallet className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Connected Wallet</p>
                      <p className="font-mono text-sm font-semibold">{walletAddress}</p>
                      {suiBalance !== null && (
                        <p className="text-xs text-primary mt-1">
                          {suiBalance.toFixed(3)} SUI
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-muted-foreground">Network</p>
                    <p className="font-semibold text-sm">Testnet</p>
                  </div>
                </div>
              </div>
            )}

            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
              <div>
                <h1 className="font-display text-3xl md:text-4xl font-bold mb-2">
                  Creator Dashboard
                </h1>
                <p className="text-muted-foreground">
                  Manage your voices and track your earnings
                </p>
              </div>
              <Link to="/upload">
                <Button variant="default">
                  <Plus className="h-5 w-5" />
                  Create New Voice
                </Button>
              </Link>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatsCard
                title="Total Earnings"
                value={`${voices.reduce((acc, v) => acc + 0, 0)} SUI`}
                change="0 SUI this month"
                changeType="neutral"
                icon={DollarSign}
              />
              <StatsCard
                title="Active Voices"
                value={voices.length.toString()}
                change={isVoicesLoading ? "Loading..." : "Registered on-chain"}
                changeType="neutral"
                icon={Mic}
              />
              <StatsCard
                title="Total Uses"
                value="0"
                change="0 this week"
                changeType="neutral"
                icon={Users}
              />
              <StatsCard
                title="Avg. Response"
                value="--s"
                change="Not enough data"
                changeType="neutral"
                icon={Clock}
              />
            </div>

            {/* x402 Earnings Banner */}
            {connected && (
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-5 mb-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary/15">
                    <Zap className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-semibold text-sm">x402 Pay-Per-Use Revenue</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Casual users pay micropayments for 2-use sessions. No subscription needed.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-center">
                  <div>
                    <p className="text-xs text-muted-foreground">Micropayments</p>
                    <p className="text-lg font-bold text-primary">—</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Active passes</p>
                    <p className="text-lg font-bold">—</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Conversions</p>
                    <p className="text-lg font-bold">—</p>
                  </div>
                </div>
              </div>
            )}

            {/* Chart and Activity */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              <div className="lg:col-span-2">
                <UsageChart />
              </div>
              <div className="glass-card p-6">
                <h3 className="font-display text-lg font-semibold mb-4">Recent Activity</h3>
                <div className="space-y-4">
                  {recentActivity.map((activity, index) => (
                    <div key={index} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                      <div>
                        <p className="text-sm font-medium">{activity.voice}</p>
                        <p className="text-xs text-muted-foreground">{activity.time}</p>
                      </div>
                      <span className={`text-sm font-semibold ${activity.type === 'payout' ? 'text-green-500' : 'text-primary'
                        }`}>
                        +{activity.amount} SUI
                      </span>
                    </div>
                  ))}
                </div>
                <Button variant="ghost" size="sm" className="w-full mt-4">
                  View All Activity
                </Button>
              </div>
            </div>

            {/* Voice Models */}
            <div className="glass-card p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-display text-lg font-semibold">Your Voice Models</h3>
                <Button variant="ghost" size="sm">
                  <Settings className="h-4 w-4 mr-2" />
                  Manage
                </Button>
              </div>
              <div className="space-y-4">
                {isVoicesLoading ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>Loading your voices...</p>
                  </div>
                ) : voices.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>You haven't created any voices yet.</p>
                  </div>
                ) : (
                  voices.map((voice) => (
                    <div
                      key={voice.voiceId}
                      className="flex flex-col md:flex-row md:items-center justify-between p-4 rounded-xl bg-muted/50 gap-4"
                    >
                      <div className="flex items-center gap-4">
                        <div className="p-3 rounded-xl bg-primary/10">
                          <Mic className="h-6 w-6 text-primary" />
                        </div>
                        <div>
                          <h4 className="font-semibold">{voice.name}</h4>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-500">
                              active
                            </span>
                            <span className="text-sm text-muted-foreground">
                              {voice.pricePerUse} SUI/use
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <p className="text-sm text-muted-foreground">Uses</p>
                          <p className="font-semibold">0</p>
                        </div>
                        <div className="text-center">
                          <p className="text-sm text-muted-foreground">Earnings</p>
                          <p className="font-semibold text-primary">0 SUI</p>
                        </div>
                        <Button variant="outline" size="sm">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </>
  );
};

export default Dashboard;
