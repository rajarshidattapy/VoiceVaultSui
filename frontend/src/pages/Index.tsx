import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import { HeroSection } from "@/components/landing/HeroSection";
import { FeaturesSection } from "@/components/landing/FeaturesSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { CTASection } from "@/components/landing/CTASection";
import { Helmet } from "react-helmet-async";

const Index = () => {
  return (
    <>
      <Helmet>
        <title>VoiceVault - Own Your Voice. Deploy Your Agent. Earn Forever.</title>
        <meta name="description" content="Train a custom AI voice model, mint on-chain ownership on Sui, deploy a LiveKit voice agent, and earn per call — via full licenses or x402 micropayments." />
      </Helmet>
      <div className="min-h-screen bg-background">
        <Navbar />
        <main>
          <HeroSection />
          <FeaturesSection />
          <HowItWorksSection />
          <CTASection />
        </main>
        <Footer />
      </div>
    </>
  );
};

export default Index;
