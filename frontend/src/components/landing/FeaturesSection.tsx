import { Mic, Shield, Bot, Zap, Coins, Globe } from "lucide-react";

const features = [
  {
    icon: Mic,
    title: "Clone Your Voice",
    description: "Upload audio, get a custom AI model stored forever on Walrus.",
    color: "primary",
  },
  {
    icon: Bot,
    title: "Deploy an Agent",
    description: "Pick a template, pick an LLM, go live. Your voice works 24/7.",
    color: "secondary",
  },
  {
    icon: Zap,
    title: "x402 Pay-Per-Use",
    description: "No subscription. Callers pay per session, instantly, on Sui.",
    color: "primary",
  },
  {
    icon: Shield,
    title: "On-Chain Ownership",
    description: "VoiceIdentity NFT on Sui. Buyers get a LicensePass — no middlemen.",
    color: "secondary",
  },
  {
    icon: Coins,
    title: "Auto Royalty Split",
    description: "Every payment splits on-chain: 2.5% platform, 10% royalty, rest to you.",
    color: "primary",
  },
  {
    icon: Globe,
    title: "Global Marketplace",
    description: "All voices live in an on-chain registry — discoverable by anyone, anywhere.",
    color: "secondary",
  },
];

export function FeaturesSection() {
  return (
    <section className="py-24 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-background via-card/30 to-background" />
      <div className="container relative z-10 mx-auto px-4">
        <div className="text-center max-w-xl mx-auto mb-14">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-3">
            Everything you need to{" "}
            <span className="gradient-text">monetize your voice</span>
          </h2>
          <p className="text-muted-foreground text-sm">
            Own it. Deploy it. Earn from it.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className="glass-card-hover p-6 group"
              style={{ animationDelay: `${index * 0.08}s` }}
            >
              <div className={`inline-flex p-3 rounded-xl mb-3 ${feature.color === "primary"
                  ? "bg-primary/10 text-primary"
                  : "bg-secondary/10 text-secondary"
                } group-hover:scale-110 transition-transform duration-300`}>
                <feature.icon className="h-5 w-5" />
              </div>
              <h3 className="font-display text-base font-semibold mb-1">{feature.title}</h3>
              <p className="text-sm text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
