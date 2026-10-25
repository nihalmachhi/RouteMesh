import { useEffect, useState } from "react";

const links = [
  ["Policies", "#policies"], ["Decisions", "#reasons"], ["Failure", "#failure"],
  ["Features", "#features"], ["Quick start", "#start"], ["FAQ", "#faq"],
] as const;

export function SiteHeader({ motionPaused, onToggleMotion }: { motionPaused: boolean; onToggleMotion: () => void }) {
  const [theme, setTheme] = useState<"light" | "dark" | "system">(() => {
    const stored = window.localStorage.getItem("routemesh-theme");
    return stored === "light" || stored === "dark" ? stored : "system";
  });

  useEffect(() => {
    if (theme === "system") document.documentElement.removeAttribute("data-theme");
    else document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  function toggleTheme() {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const next = theme === "system" ? (prefersDark ? "light" : "dark") : theme === "dark" ? "light" : "dark";
    window.localStorage.setItem("routemesh-theme", next);
    setTheme(next);
  }

  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <header className="site-header">
        <div className="wrap header-inner">
          <a className="brand" href="#top" aria-label="RouteMesh home"><img className="brand-mark" src="/readme-icon.png" alt="" width="30" height="30" />RouteMesh</a>
          <nav className="site-nav" aria-label="Sections">
            {links.map(([label, href]) => <a href={href} key={href}>{label}</a>)}
          </nav>
          <div className="header-tools">
            <button className="button button-quiet button-small pause-button" type="button" onClick={onToggleMotion} aria-pressed={motionPaused}>
              <span aria-hidden="true">{motionPaused ? "▶" : "Ⅱ"}</span><span className="pause-label">{motionPaused ? "Play animations" : "Pause animations"}</span>
            </button>
            <button className="button button-quiet button-small theme-button" type="button" onClick={toggleTheme} aria-label="Toggle color theme">
              <span aria-hidden="true">◐</span><span className="theme-label">Theme</span>
            </button>
            <a className="button button-dark button-small" href="https://github.com/nihalmachhi/RouteMesh" target="_blank" rel="noreferrer">GitHub</a>
          </div>
        </div>
      </header>
    </>
  );
}
