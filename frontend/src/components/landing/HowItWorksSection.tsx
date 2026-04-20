import { Upload, Link2, Bot, Coins, ArrowRight, Zap } from "lucide-react";

const creatorSteps = [
  {
    step: "01",
    icon: Upload,
    title: "Upload Your Voice",
    description:
      "Record or upload 10–30 minutes of clean audio. Our AI processes it into a custom voice model.",
  },
  {
    step: "02",
    icon: Link2,
    title: "Mint On-Chain",
    description:
      "Register your voice as a VoiceIdentity NFT on Sui. Instant global discoverability via the on-chain registry.",
  },
  {
    step: "03",
    icon: Bot,
    title: "Deploy a Voice Agent",
    description:
      "Pick a template (Sales, Support, Tutor…), configure an LLM and price per call, and deploy a live LiveKit voice agent in seconds.",
  },
  {
    step: "04",
    icon: Coins,
    title: "Earn Every Call",
    description:
      "Royalties split on-chain automatically — from full license purchases, x402 micropayments, and per-agent-call fees.",
  },
];

const callerSteps = [
  {
    icon: Zap,
    title: "Try · 0.1 SUI",
    description: "Click Try on any voice in the marketplace. Pay 0.1 SUI and get 2 instant generations — no checkout, no account.",
  },
  {
    icon: Bot,
    title: "Talk to an Agent",
    description: "Find a deployed voice agent, pay per call on-chain, and talk live via a browser — no app needed.",
  },
  {
    icon: Link2,
    title: "Buy Full License",
    description: "When you want unlimited access, buy the full LicensePass NFT. It lives in your wallet as permanent proof of rights.",
  },
];

export function HowItWorksSection() {
  return (
    <section className="py-24 relative overflow-hidden">
      <div className="container mx-auto px-4 space-y-20">

        {/* Creator Path */}
        <div>
          <div className="text-center max-w-2xl mx-auto mb-16">
            <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
              For <span className="gradient-text">Creators</span>
            </h2>
            <p className="text-muted-foreground">
              From voice upload to a live earning agent in four steps
            </p>
          </div>

          <div className="relative">
            <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-primary/20 via-primary to-secondary/20 -translate-y-1/2" />

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
              {creatorSteps.map((step, index) => (
                <div key={step.step} className="relative">
                  <div className="glass-card p-6 text-center relative z-10 h-full">
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-background px-3 py-1 rounded-full border border-primary/30">
                      <span className="font-display text-sm font-bold text-primary">
                        {step.step}
                      </span>
                    </div>
                    <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/20 mb-4 mt-4">
                      <step.icon className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="font-display text-lg font-semibold mb-2">
                      {step.title}
                    </h3>
                    <p className="text-sm text-muted-foreground">{step.description}</p>
                  </div>
                  {index < creatorSteps.length - 1 && (
                    <div className="hidden lg:flex absolute top-1/2 -right-4 -translate-y-1/2 z-20">
                      <ArrowRight className="h-6 w-6 text-primary" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Caller / User Path */}
        <div>
          <div className="text-center max-w-2xl mx-auto mb-12">
            <h2 className="font-display text-3xl md:text-4xl font-bold mb-4">
              For <span className="gradient-text">Callers &amp; Users</span>
            </h2>
            <p className="text-muted-foreground">
              No subscriptions. Pay only for what you use.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
            {callerSteps.map((item) => (
              <div
                key={item.title}
                className="glass-card-hover p-6 text-center group"
              >
                <div className="inline-flex p-3 rounded-xl bg-primary/10 text-primary mb-4 group-hover:scale-110 transition-transform duration-300">
                  <item.icon className="h-6 w-6" />
                </div>
                <h3 className="font-display text-base font-semibold mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
