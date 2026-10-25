export function ClosingSection() {
  return (
    <section className="wrap closing-section">
      <div className="closing-panel">
        <svg viewBox="0 0 560 190" role="img" aria-label="A client sends requests to RouteMesh, which routes them to three backends">
          <rect className="node" x="6" y="68" width="92" height="54" rx="14" /><text x="52" y="100" textAnchor="middle">client</text>
          <rect className="proxy-node" x="200" y="55" width="130" height="80" rx="18" /><text x="265" y="100" textAnchor="middle">RouteMesh</text>
          <rect className="node" x="440" y="8" width="114" height="46" rx="14" /><text x="497" y="36" textAnchor="middle">backend-a</text>
          <rect className="node" x="440" y="72" width="114" height="46" rx="14" /><text x="497" y="100" textAnchor="middle">backend-b</text>
          <rect className="node" x="440" y="136" width="114" height="46" rx="14" /><text x="497" y="164" textAnchor="middle">backend-c</text>
          <path className="flow-line" d="M98 95H200" /><path className="flow-line" d="M330 80C390 80 390 31 440 31" />
          <path className="flow-line" d="M330 95H440" /><path className="flow-line" d="M330 110C390 110 390 159 440 159" />
        </svg>
        <h2>Break a backend. Watch the routing change.</h2>
        <div className="button-row centered-actions"><a className="button button-dark" href="https://github.com/nihalmachhi/RouteMesh" target="_blank" rel="noreferrer">View on GitHub</a><a className="button button-quiet" href="#demo">Back to the simulator</a></div>
      </div>
    </section>
  );
}
