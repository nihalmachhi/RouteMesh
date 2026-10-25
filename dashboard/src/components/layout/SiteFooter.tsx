export function SiteFooter() {
  return (
    <footer className="site-footer"><div className="wrap"><div className="footer-panel">
      <div className="footer-top">
        <div><a className="brand footer-brand" href="#top">RouteMesh</a><p>An observable application-level reverse proxy for learning how routing policies behave.</p></div>
        <FooterLinks title="Product" links={[["Simulator", "#demo"], ["Policies", "#policies"], ["Decisions", "#reasons"], ["Failure handling", "#failure"], ["Features", "#features"]]} />
        <FooterLinks title="Run it" links={[["Quick start", "#start"], ["FAQ", "#faq"]]} />
        <FooterLinks title="Source" links={[["GitHub", "https://github.com/nihalmachhi/RouteMesh"], ["Architecture", "https://github.com/nihalmachhi/RouteMesh/blob/main/docs/architecture.md"], ["Decisions", "https://github.com/nihalmachhi/RouteMesh/tree/main/docs/decisions"], ["Benchmarks", "https://github.com/nihalmachhi/RouteMesh/blob/main/docs/benchmarks/results.md"]]} />
      </div>
      <div className="footer-fine"><span>Prototype landing page. The simulator is not connected to a live proxy.</span><span>FastAPI · HTTPX · Prometheus · React</span></div>
      <div className="footer-wordmark" aria-hidden="true">RouteMesh</div>
    </div></div></footer>
  );
}

function FooterLinks({ title, links }: { title: string; links: [string, string][] }) {
  return <nav aria-label={title}><h2>{title}</h2><ul>{links.map(([label, href])=><li key={href}><a href={href} target={href.startsWith("http") ? "_blank" : undefined} rel={href.startsWith("http") ? "noreferrer" : undefined}>{label}</a></li>)}</ul></nav>;
}
