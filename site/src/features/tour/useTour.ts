import { useEffect, useState } from "react";

export interface TourState {
  active: number;
  setActive: (index: number) => void;
  paused: boolean;
  setPaused: (paused: boolean) => void;
  holding: boolean;
}

export function useTour(tabCount: number): TourState {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(() =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [holding, setHolding] = useState(false);

  useEffect(() => {
    if (paused || holding || tabCount < 2) return undefined;
    const timer = window.setInterval(() => setActive((index) => (index + 1) % tabCount), 7000);
    return () => window.clearInterval(timer);
  }, [paused, holding, tabCount]);

  useEffect(() => {
    const targets = [document.getElementById("win"), document.getElementById("tl")].filter(
      (element): element is HTMLElement => element !== null,
    );
    const pause = () => setHolding(true);
    const resume = () => setHolding(false);
    const visibility = () => setHolding(document.hidden);
    targets.forEach((target) => {
      target.addEventListener("mouseenter", pause);
      target.addEventListener("mouseleave", resume);
      target.addEventListener("focusin", pause);
      target.addEventListener("focusout", resume);
    });
    document.addEventListener("visibilitychange", visibility);
    return () => {
      targets.forEach((target) => {
        target.removeEventListener("mouseenter", pause);
        target.removeEventListener("mouseleave", resume);
        target.removeEventListener("focusin", pause);
        target.removeEventListener("focusout", resume);
      });
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);

  return { active, setActive, paused, setPaused, holding };
}
