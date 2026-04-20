import { Button } from "@/components/ui/button";
import { ArrowRight, Play, Bot, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import heroWaves from "@/assets/freq.mp4";

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Background Effects */}
      <div className="absolute inset-0">
        <video
          src={heroWaves}
          autoPlay
          loop
          muted
          playsInline
          className="absolute inset-0 w-full h-full object-cover opacity-50"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background/60 via-background/40 to-background/80" />
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/30 rounded-full blur-[128px] animate-pulse-glow" />
        <div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-400/20 rounded-full blur-[128px] animate-pulse-glow"
          style={{ animationDelay: "1s" }}
        />
      </div>

      <div className="container relative z-10 mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 mb-8 animate-fade-in">
            <img src="/sui.png" alt="Sui" className="h-5 w-5 rounded-full object-cover" />
            <span className="text-sm font-medium text-blue-500">
              Powered by Sui and Walrus
            </span>
          </div>

          {/* Heading */}
          <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-bold mb-6 animate-slide-up">
            Own Your Voice.
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
              Deploy Your Agent.
            </span>
            <br />
              Earn Forever.
          </h1>

          {/* Subheading */}
          <p
            className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-4 animate-slide-up"
            style={{ animationDelay: "0.1s" }}
          >
            Train a custom AI voice model, mint on-chain ownership on Sui, and deploy an
            autonomous voice agent — then earn every time someone calls it.
          </p>

          {/* x402 pill */}
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 border border-primary/20 mb-10 animate-slide-up text-sm text-primary font-medium"
            style={{ animationDelay: "0.15s" }}
          >
            <Zap className="h-3.5 w-3.5" />
            New: x402 pay-per-use — callers pay per call, no subscription needed
          </div>

          {/* CTAs */}
          <div
            className="flex flex-col sm:flex-row gap-4 justify-center mb-16 animate-slide-up"
            style={{ animationDelay: "0.2s" }}
          >
            <Link to="/upload">
              <Button size="xl" className="bg-blue-500 hover:bg-blue-600 text-white">
                Create Your Voice
                <ArrowRight className="h-5 w-5" />
              </Button>
            </Link>
            <Link to="/deploy">
              <Button
                size="xl"
                className="bg-white/10 hover:bg-white/20 backdrop-blur border border-white/20"
              >
                <Bot className="h-5 w-5" />
                Deploy Agent
              </Button>
            </Link>
            <Link to="/marketplace">
              <Button
                size="xl"
                variant="ghost"
                className="border border-white/10 hover:bg-white/10"
              >
                <Play className="h-5 w-5" />
                Explore Voices
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div
            className="grid grid-cols-3 gap-8 max-w-lg mx-auto animate-slide-up"
            style={{ animationDelay: "0.3s" }}
          >
            <div className="text-center">
              <div className="font-display text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
                2.4K+
              </div>
              <div className="text-sm text-muted-foreground mt-1">Voice Models</div>
            </div>
            <div className="text-center">
              <div className="font-display text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
                $840K
              </div>
              <div className="text-sm text-muted-foreground mt-1">Creator Earnings</div>
            </div>
            <div className="text-center">
              <div className="font-display text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
                12M+
              </div>
              <div className="text-sm text-muted-foreground mt-1">Agent Calls</div>
            </div>
          </div>
        </div>
      </div>

      {/* Scroll Indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
        <div className="w-6 h-10 rounded-full border-2 border-muted-foreground/30 flex items-start justify-center p-2">
          <div className="w-1 h-2 bg-blue-500 rounded-full animate-pulse" />
        </div>
      </div>
    </section>
  );
}
