import { useEffect, useState } from "react";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { useSimulator } from "@/features/simulator/useSimulator";
import { ClosingSection } from "@/sections/ClosingSection";
import { DecisionSection } from "@/sections/DecisionSection";
import { FAQSection } from "@/sections/FAQSection";
import { FailureSection } from "@/sections/FailureSection";
import { FeatureGrid } from "@/sections/FeatureGrid";
import { HeroSection } from "@/sections/HeroSection";
import { PolicySection } from "@/sections/PolicySection";
import { QuickStartSection } from "@/sections/QuickStartSection";
import { ScopeSection } from "@/sections/ScopeSection";
import type { BackendMode } from "@/features/simulator/model";

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function DashboardPage() {
  const simulator = useSimulator();
  const [motionPaused, setMotionPaused] = useState(prefersReducedMotion);

  useEffect(() => {
    document.documentElement.dataset.motion = motionPaused ? "off" : "on";
    return () => { delete document.documentElement.dataset.motion; };
  }, [motionPaused]);

  function tryPolicy(policy: Parameters<typeof simulator.choosePolicy>[0]) {
    simulator.choosePolicy(policy);
    document.getElementById("demo")?.scrollIntoView({ behavior: motionPaused ? "auto" : "smooth", block: "start" });
  }

  function breakBackend(id: string, mode: BackendMode) {
    simulator.setBackendMode(id, mode);
    simulator.setAutoTraffic(true);
    document.getElementById("demo")?.scrollIntoView({ behavior: motionPaused ? "auto" : "smooth", block: "start" });
  }

  return <>
    <SiteHeader motionPaused={motionPaused} onToggleMotion={() => setMotionPaused((paused) => !paused)} />
    <main id="main">
      <HeroSection state={simulator.state} onPolicy={simulator.choosePolicy} onAuto={simulator.toggleAutoTraffic} onBurst={simulator.sendBurst} onReset={simulator.reset} onBackendMode={simulator.setBackendMode} />
      <PolicySection state={simulator.state} onTryPolicy={tryPolicy} />
      <DecisionSection state={simulator.state} onPolicy={tryPolicy} />
      <FailureSection onBreak={breakBackend} />
      <FeatureGrid />
      <QuickStartSection />
      <ScopeSection />
      <FAQSection />
      <ClosingSection />
    </main>
    <SiteFooter />
  </>;
}
