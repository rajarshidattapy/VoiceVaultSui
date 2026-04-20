import { Mic, Shield, Coins, Globe, Bot, Zap } from "lucide-react";

const features = [
  {
    icon: Mic,
    title: "Voice Cloning",
    description:
      "Upload audio samples and train a custom AI voice model that sounds exactly like you — stored permanently on Walrus.",
    color: "primary",
  },
  {
    icon: Bot,
    title: "Voice Agent Deployment",
    description:
      "Turn your voice into a live AI agent. Pick a template (Sales, Support, Tutor, Creator Clone), configure an LLM, and deploy — callers talk to your voice 24/7 via LiveKit.",
    color: "secondary",
  },
  {
    icon: Shield,
    title: "On-Chain Ownership",
    description:
      "Your voice is minted as a VoiceIdentity NFT on Sui. Buyers receive a LicensePass NFT — cryptographic proof of rights, no middlemen.",
    color: "primary",
  },
  {
    icon: Zap,
    title: "x402 Pay-Per-Use",
    description:
      "No subscription required. Callers pay per session via HTTP 402 micropayments on Sui — instant access, 2 uses unlocked, upsell to full license.",
    color: "secondary",
  },
  {
    icon: Coins,
    title: "Automatic Royalty Split",
    description:
      "Every payment — license purchase or x402 micropayment — auto-splits on-chain: 2.5% platform fee, 10% royalty, remainder straight to you.",
    color: "primary",
  },
  {
    icon: Globe,
    title: "Global Marketplace",
    description:
      "All registered voices are discoverable from an on-chain VoiceRegistry shared object — no localStorage, visible to everyone worldwide instantly.",
    color: "secondary",
  },
];

export function FeaturesSection() {
  return (
    <section className="py-24 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-background via-card/30 to-background" />

      <div className="container relative z-10 mx-auto px-4">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
            The Full Stack for{" "}
            <span className="gradient-text">Voice Monetization</span>
          </h2>
          <p className="text-muted-foreground">
            Own your voice on-chain, deploy autonomous agents, and earn — from full
            licenses to x402 micropayments — all without a middleman.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className="glass-card-hover p-6 group"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div
                className={`inline-flex p-3 rounded-xl mb-4 ${
                  feature.color === "primary"
                    ? "bg-primary/10 text-primary"
                    : "bg-secondary/10 text-secondary"
                } group-hover:scale-110 transition-transform duration-300`}
              >
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="font-display text-lg font-semibold mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
