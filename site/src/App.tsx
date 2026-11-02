import { useEffect, useMemo, useState, type CSSProperties, type KeyboardEvent } from "react";
import { content } from "./data/content";
import { runSimulation, type BackendSignal, type PolicyName, type SimulationResult } from "./features/simulator/engine";

const policyNames: Record<PolicyName, string> = {
  round_robin: "Round robin",
  least_connections: "Least connections",
  latency_aware: "Latency aware",
};
const initialBackends: BackendSignal[] = [
  { backend_id: "backend-a", url: "http://backend-a:9001", healthy: true, circuit_state: "closed", in_flight: 0, ewma_latency_ms: 24, cpu_percent: 22, error_rate: 0.02, failure_rate: 0.01 },
  { backend_id: "backend-b", url: "http://backend-b:9002", healthy: true, circuit_state: "closed", in_flight: 0, ewma_latency_ms: 58, cpu_percent: 55, error_rate: 0.04, failure_rate: 0.04 },
  { backend_id: "backend-c", url: "http://backend-c:9003", healthy: true, circuit_state: "closed", in_flight: 0, ewma_latency_ms: 35, cpu_percent: 34, error_rate: 0.03, failure_rate: 0.02 },
];
const glyphs: Record<string, string> = {
  route: "M4 6h6l3 6h7M4 18h6l3-6M17 9l3 3-3 3",
  shield: "M12 3 20 6v5c0 5-3.4 8.5-8 10-4.6-1.5-8-5-8-10V6z",
  chart: "M4 19V5m0 14h17M8 15l3-4 3 2 6-7",
  check: "m5 12 4 4L19 6",
  server: "M4 5h16v6H4zM4 14h16v5H4zM7 8h.01M7 17h.01M11 8h6M11 17h6",
  pulse: "M3 12h4l3-8 4 16 3-8h4",
  database: "M4 6c0-2 3.6-3 8-3s8 1 8 3-3.6 3-8 3-8-1-8-3zm0 0v6c0 2 3.6 3 8 3s8-1 8-3V6m-16 6v6c0 2 3.6 3 8 3s8-1 8-3v-6",
  arrow: "M5 12h14m-6-6 6 6-6 6",
};
function Icon({ name }: { name: string }) {
  return <svg className="icon" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d={glyphs[name] ?? glyphs.arrow}/></svg>;
}
function Brand() {
  return <a className="brand" href="#top"><img className="brand-icon" src={import.meta.env.BASE_URL+"readme-icon.png"} alt="" width="22" height="22"/>RouteMesh</a>;
}
function TabPanel({ active, result }: { active: number; result: SimulationResult | null }) {
  const tab = content.tour.tabs[active]!;
  const title = tab.title;
  const lines = tab.rows;
  return <div className="body">
    <div className="col cv">
      <h3>{title}</h3><div className="sub">{tab.subtitle}</div>
      <div className="shead"><span>BACKEND / SIGNAL</span><span>LOAD</span><span>STATE</span></div>
      {lines.map((row,i)=><div className="sp-r rise" style={{"--i":i+1} as CSSProperties} key={row.id}>
        <span className={"ib gn st "+(row.tone==="bad"?"bad":"") } style={{"--c":row.tone==="bad"?"var(--bad)":row.tone==="warm"?"#fbbf24":"var(--ok)"} as CSSProperties}><Icon name={row.tone==="bad"?"shield":"server"}/></span>
        <b>{row.id}</b><span className="ms">{row.latency}</span><span className="ms">{row.load}</span><span className={row.tone==="bad"?"no":"ok"}>{row.status}</span>
      </div>)}
      <p className="tx rise">{tab.badge}</p>
    </div>
    <div className="col cv">
      <h4>{tab.asideTitle}</h4><p className="tx">{tab.asideLines[0]}</p>
      <ul className="lst">{tab.asideLines.slice(1).map(line=><li key={line}>{line}</li>)}</ul>
      {result && <div className="mini"><b>LAST LOCAL RUN</b><br/>selected policy · {policyNames[result.policy]}<br/>synthetic errors · {result.errors} / {result.total}</div>}
    </div>
  </div>;
}
function resultFor(policy: PolicyName, backends: BackendSignal[], count: number, rate: number, seed: number): SimulationResult | null {
  try { return runSimulation({ policy, backends, requestCount: count, arrivalRate: rate, seed }); }
  catch { return null; }
}
function ResultMetrics({ result, label }: { result: SimulationResult | null; label: string }) {
  return <div className="scc"><h3>{label}</h3>{result ? <>
    <div className="stats"><div className="stat"><span>p50 latency</span><b>{result.p50.toFixed(1)} ms</b></div><div className="stat"><span>p99 latency</span><b>{result.p99.toFixed(1)} ms</b></div><div className="stat"><span>errors</span><b>{result.errors} / {result.total}</b></div></div>
    <div className="share-list">{result.shares.map((s,i)=><div className="m" key={s.backend_id}><div className="mr"><span>{s.backend_id}</span><b>{s.count} ({s.percentage.toFixed(0)}%)</b></div><div className="track"><div className="grow" style={{"--w":s.percentage+"%","--c":["var(--accent)","#a78bfa","#4ade9a"][i]} as CSSProperties}/></div><small>{s.circuit_state==="open"?"circuit open":"circuit closed"}</small></div>)}</div>
  </> : <div className="empty">No healthy backend is eligible.</div>}</div>;
}

export function App() {
  const [active,setActive]=useState(0);
  const [paused,setPaused]=useState(()=>window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const [holding,setHolding]=useState(false);
  const [policy,setPolicy]=useState<PolicyName>("latency_aware");
  const [arrival,setArrival]=useState(30);
  const [requestCount,setRequestCount]=useState(60);
  const [latency,setLatency]=useState([24,58,35]);
  
  const [failure,setFailure]=useState([1,4,2]);
  const [offline,setOffline]=useState([false,false,false]);
  const [run,setRun]=useState(0);
  const [shell,setShell]=useState<"powershell"|"bash">("powershell");

  const backends=useMemo(()=>initialBackends.map((b,i)=>({...b,ewma_latency_ms:latency[i]??24,error_rate:(failure[i]??0)/100,failure_rate:(failure[i]??0)/100,healthy:!offline[i],circuit_state:offline[i]?"open" as const:"closed" as const})) ,[latency,failure,offline]);
  const seed=2026+run;
  const selected=useMemo(()=>resultFor(policy,backends,requestCount,arrival,seed),[policy,backends,requestCount,arrival,seed]);
  const comparePolicy:PolicyName=policy==="round_robin"?"least_connections":"round_robin";
  const comparison=useMemo(()=>resultFor(comparePolicy,backends,requestCount,arrival,seed),[comparePolicy,backends,requestCount,arrival,seed]);

  useEffect(()=>{if(paused||holding)return undefined;const timer=window.setInterval(()=>setActive(index=>(index+1)%content.tour.tabs.length),7000);return()=>window.clearInterval(timer)},[paused,holding]);
  useEffect(()=>{const targets=[document.getElementById("win"),document.getElementById("tl")].filter((x):x is HTMLElement=>x!==null);const pause=()=>setHolding(true);const resume=()=>setHolding(false);const visibility=()=>setHolding(document.hidden);targets.forEach(target=>{target.addEventListener("mouseenter",pause);target.addEventListener("mouseleave",resume);target.addEventListener("focusin",pause);target.addEventListener("focusout",resume)});document.addEventListener("visibilitychange",visibility);return()=>{targets.forEach(target=>{target.removeEventListener("mouseenter",pause);target.removeEventListener("mouseleave",resume);target.removeEventListener("focusin",pause);target.removeEventListener("focusout",resume)});document.removeEventListener("visibilitychange",visibility)}},[]);
  useEffect(()=>{const target=document.querySelector(".rv-wrap");if(!target||!("IntersectionObserver"in window))return;const observer=new IntersectionObserver(([entry])=>{if(entry?.isIntersecting){target.classList.add("in");observer.disconnect()}},{threshold:.25});observer.observe(target);return()=>observer.disconnect()},[]);
  function handleTabKeys(event:KeyboardEvent<HTMLDivElement>){const next=event.key==="ArrowRight"?(active+1)%content.tour.tabs.length:event.key==="ArrowLeft"?(active-1+content.tour.tabs.length)%content.tour.tabs.length:event.key==="Home"?0:event.key==="End"?content.tour.tabs.length-1:-1;if(next>=0){event.preventDefault();setActive(next);document.getElementById("tour-tab-"+next)?.focus()}}
  const tour=content.tour.tabs[active]!;

  return <>
    <div className="wrap">
      <nav className="top" aria-label="Main"><Brand/><div className="links">{content.navigation.map(item=><a href={item.href} key={item.href}>{item.label}</a>)}</div><div className="sp"><a className="pill" href="https://github.com/nihalmachhi/RouteMesh" target="_blank" rel="noreferrer">GitHub</a><a className="pill w" href="#start">Run it locally</a></div></nav>
      <header className={"hero"+(paused||holding?" hold":"")} id="top">
        <h1>{content.hero.title}</h1><p>Route healthy traffic with explainable policies, circuit breakers, and bounded retries.</p>
        <div className="cta"><a className="pill w" href="#try">Try the load lab</a><a className="pill" href="#start">Run it locally</a></div>
        <div className="tabs"><div className="tl" id="tl" role="tablist" tabIndex={0} aria-label="RouteMesh routing walkthrough" onKeyDown={handleTabKeys}>{content.tour.tabs.map((item,index)=><button type="button" className="tab" role="tab" id={"tour-tab-"+index} aria-selected={active===index} aria-controls="tour-panel" tabIndex={active===index?0:-1} onClick={()=>setActive(index)} key={item.id}>{item.label}<i className="bar"/></button>)}</div><button type="button" className="ctrl" onClick={()=>setPaused(value=>!value)} aria-label={paused?"Resume the automatic tour":"Pause the automatic tour"} title={paused?"Resume":"Pause"}>{paused?"▶":"❚❚"}</button></div>
        <div className="win" id="win">
          <aside className="side" aria-hidden="true"><div className="dots"><i/><i/><i/></div><div className="it on">Routing <span>3</span></div><div className="it">Backends <span>3</span></div><div className="it">Policies <span>3</span></div><div className="it">Decisions <span>↗</span></div><h4>HEALTH</h4>{backends.map((backend,i)=><div className="it f" style={{"--c":i===2?"var(--bad)":"var(--ok)"} as CSSProperties} key={backend.backend_id}>{backend.backend_id}</div>)}</aside>
          <div className="main" id="tour-panel" role="tabpanel" aria-live="off" aria-labelledby={"tour-tab-"+active} key={tour.id}><TabPanel active={active} result={selected}/></div>
        </div>
      </header>
      <main id="main">
        <section className="sec" id="how"><h2>Three stages. <span className="m">One <Icon name="route"/> explainable route.</span></h2><p className="lead2">Every request is filtered, routed by policy, and forwarded with its decision reason kept beside the outcome.</p><div className="steps">{content.pipeline.steps.map((step,i)=><article className="step" key={step.title}><div className="ib" style={{"--c":["#8b5cf6","#f59e0b","#38bdf8"][i]} as CSSProperties}><Icon name={i===0?"shield":i===1?"route":"pulse"}/></div><h3>{step.title}</h3><p>{step.description}</p><div className="mini">{step.mini.map((line,j)=><span key={line}>{j>0&&<br/>}{line}</span>)}</div></article>)}</div></section>
        <section className="sec" id="try"><h2>Change the signals. <span className="m">Watch policies respond.</span></h2><p className="lead2">An entirely local, seeded model using the three policies implemented in RouteMesh. It sends no requests to the proxy.</p><div className="sim"><div className="scols"><div className="scc"><h3>Load lab controls</h3><label className="ctl-label" htmlFor="policy">Routing policy</label><select className="field" id="policy" value={policy} onChange={event=>setPolicy(event.target.value as PolicyName)}>{Object.entries(policyNames).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select><label className="ctl range-label">Arrival rate <b>{arrival} req/s</b><input type="range" min="5" max="100" step="5" value={arrival} onChange={event=>setArrival(+event.target.value)}/></label><label className="ctl range-label">Requests <b>{requestCount}</b><input type="range" min="10" max="120" step="10" value={requestCount} onChange={event=>setRequestCount(+event.target.value)}/></label><div className="backend-controls"><span className="eyebrow">BACKEND SIGNALS</span><div className="shead"><span>BACKEND</span><span>LATENCY</span><span>FAILURE</span><span>LIVE</span></div>{backends.map((backend,i)=><div className="backend-control" key={backend.backend_id}><b>{backend.backend_id}</b><label><span className="sr-only">{backend.backend_id} latency in milliseconds</span><input type="number" min="1" max="500" value={latency[i]} onChange={event=>setLatency(values=>values.map((v,n)=>n===i?+event.target.value:v))}/>ms</label><label><span className="sr-only">{backend.backend_id} failure percent</span><input type="number" min="0" max="100" step=".5" value={failure[i]} onChange={event=>setFailure(values=>values.map((v,n)=>n===i?+event.target.value:v))}/>%</label><button type="button" className={"switch "+(offline[i]?"off":"")} role="switch" aria-checked={!offline[i]} aria-label={"Toggle "+backend.backend_id+" availability"} onClick={()=>setOffline(values=>values.map((v,n)=>n===i?!v:v))}><i/></button></div>)}</div><button className="pill w run" onClick={()=>setRun(value=>value+1)} type="button">Run simulation <Icon name="arrow"/></button><p className="fineprint">Synthetic run · illustrative only · not a measured benchmark.</p></div><div className="scc"><div className="lab-heading"><span className="eyebrow">LIVE SIMULATION OUTPUT</span><span>RUN {String(run+1).padStart(3,"0")}</span></div><div className="comparison-policies" aria-live="polite"><ResultMetrics result={selected} label={policyNames[policy]}/><ResultMetrics result={comparison} label={policyNames[comparePolicy]}/></div><div className="feed"><h4>Recent routing decisions</h4>{selected?.feed.map(event=><div className="feed-row" key={event.request_id}><span>{event.request_id}</span><b>{event.backend_id??"no eligible backend"}</b><i className={event.succeeded?"ok":"no"}>{event.succeeded?"OK":"FAIL"}</i><small>{event.reason}</small></div>)}</div></div></div></div></section>
        <section className="sec" id="results"><h2>Measured results. <span className="m">When we have them.</span></h2><p className="lead2">No benchmark report is checked into this project, so the portfolio does not show invented performance numbers.</p><div className="rg">{[{title:"Policy comparison",body:"Locust comparison across round-robin, least-connections, and latency-aware.",status:"NOT RUN"},{title:"Parameter tuning",body:"No reproducible tuning study or confidence intervals are published yet.",status:"NOT RUN"},{title:"Retry and circuit behavior",body:"The demo can exercise failure signals; no load result is claimed here.",status:"NOT RUN"}].map(card=><article className="rc" key={card.title}><h3>{card.title}</h3><p>{card.body}</p><div className="result-status">{card.status}</div></article>)}</div><p className="note">The load lab above is synthetic. It demonstrates how implemented policies react to inputs; it is not production performance evidence.</p></section>
        <section className="sec" id="features"><h2>What RouteMesh <span className="m">does today.</span></h2><p className="lead2">{content.features.lead}</p><div className="bento">{content.features.cards.map((item,i)=><article className={"bc "+(item.span==="wide"?"w":item.span==="full"?"f":"")} key={item.title}><div className="ib" style={{"--c":["#8b5cf6","#38bdf8","#4ade9a","#f59e0b","#ef4444","#22c55e","#ec4899","#f97316"][i%8]} as CSSProperties}><Icon name={item.icon==="health"?"shield":item.icon==="explain"?"check":item.icon==="retry"?"arrow":item.icon==="limit"?"pulse":item.icon==="metrics"?"chart":item.icon==="events"?"database":"route"}/></div><h3>{item.title}</h3><p>{item.text}</p>{item.tags&&<div className="tags">{item.tags.map(tag=><span className="chip" key={tag}>{tag}</span>)}</div>}</article>)}</div></section>
        <section className="sec" id="architecture"><h2>One request. <span className="m">An inspectable path.</span></h2><p className="lead2">A single process checks backend state, selects from configured healthy targets, forwards the request, and records the result.</p><div className="archw"><svg className="flow arch" viewBox="0 0 1000 210" role="img" aria-labelledby="flow-title flow-desc"><title id="flow-title">RouteMesh request path</title><desc id="flow-desc">Client passes through health and circuit filtering, policy selection, HTTP forwarding to a configured backend, with metrics and decisions recorded. A local simulator uses the policy logic.</desc><defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#707078"/></marker></defs><path className="fl" d="M110 70H885" markerEnd="url(#arrowhead)"/>{[{x:20,t:"Client"},{x:150,t:"Health + circuit"},{x:300,t:"Policy"},{x:430,t:"HTTP forward"},{x:570,t:"Configured pool"},{x:740,t:"Metrics"},{x:860,t:"Decision log"}].map((stage,i)=><g className={"st "+(i===6?"last":"")} style={{"--d":i*.7+"s"} as CSSProperties} key={stage.t}><rect x={stage.x} y="43" width="112" height="54" rx="12"/><text x={stage.x+56} y="75" textAnchor="middle" fill="#ececee">{stage.t}</text></g>)}<path className="fl" d="M356 98V160H635V105"/><text className="branch-label" x="490" y="185" textAnchor="middle" fill="#8c8c95" fontSize="9" fontFamily="var(--fm)">LOCAL LOAD LAB · SAME THREE POLICY RULES</text></svg></div></section>
        <section className="sec" id="start"><h2>Run it locally.</h2><p className="lead2">Start the Docker Compose demo, then inspect the dashboard and proxy.</p><div className="shell-tabs" role="tablist" aria-label="Shell commands"><button role="tab" aria-selected={shell==="powershell"} onClick={()=>setShell("powershell")}>PowerShell</button><button role="tab" aria-selected={shell==="bash"} onClick={()=>setShell("bash")}>Bash</button></div><div className="steps qs">{[{title:"Start the stack",code:"docker compose up --build"},{title:"Open the dashboard",code:shell==="powershell"?"Start-Process http://localhost:3000":"open http://localhost:3000"},{title:"Try a routed request",code:shell==="powershell"?"Invoke-WebRequest http://localhost:8000/demo":"curl http://localhost:8000/demo"}].map((item,i)=><article className="step" key={item.title}><div className="ib" style={{"--c":["#38bdf8","#8b5cf6","#4ade9a"][i]} as CSSProperties}><Icon name={i===0?"server":i===1?"chart":"route"}/></div><h3>{item.title}</h3><div className="code"><code>{item.code}</code></div></article>)}</div><p className="note">Docker Desktop is required. Compose starts the proxy, three demo backends, Prometheus, and dashboard. Set ROUTEMESH_ADMIN_TOKEN in a local .env to protect admin controls.</p></section>
        <section className="sec" id="scope"><h2>A learning project. <span className="m">Clearly bounded.</span></h2><p className="lead2">RouteMesh demonstrates application-level routing and resilience controls with visible decisions.</p><div className="sc"><article className="scc"><div className="ib" style={{"--c":"var(--ok)"} as CSSProperties}><Icon name="check"/></div><h3>In scope</h3><ul>{content.scope.inScope.map(item=><li key={item}>{item}</li>)}</ul></article><article className="scc"><div className="ib" style={{"--c":"var(--bad)"} as CSSProperties}><Icon name="shield"/></div><h3>Out of scope</h3><ul>{content.scope.outScope.map(item=><li key={item}>{item}</li>)}</ul></article></div></section>
        <section className="sec" id="faq"><h2>Questions about <span className="m">the route.</span></h2><div className="faq">{content.faq.map((item,i)=><details key={item.question} open={i===0}><summary>{item.question}</summary><p>{item.answer}</p></details>)}</div></section>
        <section className="cta2 rv-wrap" aria-label="Get started"><div className="rv"><span className="eyebrow">FOLLOW THE DECISION</span><h2>Run it. Change a backend. See why the route changed.</h2><div className="btns"><a className="pill w" href="https://github.com/nihalmachhi/RouteMesh" target="_blank" rel="noreferrer">View RouteMesh on GitHub</a><a className="pill" href="#try">Back to the load lab</a></div></div></section>
      </main>
      <footer className="foot"><div className="fcols"><div><Brand/><p className="tg">A local, observable reverse proxy for learning how backend routing decisions behave.</p></div><div><h5>PROJECT</h5><ul><li><a href="https://github.com/nihalmachhi/RouteMesh">GitHub</a></li><li><a href="https://github.com/nihalmachhi/RouteMesh/issues">Issues</a></li></ul></div><div><h5>CODE</h5><ul><li><a href="https://github.com/nihalmachhi/RouteMesh/tree/main/src/routemesh">Source</a></li><li><a href="https://github.com/nihalmachhi/RouteMesh/tree/main/configs">Configuration</a></li></ul></div><div><h5>GUIDES</h5><ul><li><a href="https://github.com/nihalmachhi/RouteMesh#readme">README</a></li><li><a href="https://github.com/nihalmachhi/RouteMesh/tree/main/docs">Documentation</a></li></ul></div></div><h2 className="mark">RouteMesh</h2><div className="foot-bottom"><span>OPEN SOURCE LEARNING PROJECT · SYNTHETIC DEMO</span><a href="#top">Back to top ↑</a></div></footer>
    </div>
  </>;
}
