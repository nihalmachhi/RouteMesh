import { useState } from "react";

const commands = [
  { id: "stack", title: "Start the stack", code: "docker compose up --build" },
  { id: "dashboard", title: "Open the dashboard", code: "http://localhost:3000", note: "API docs: localhost:8000/docs · metrics: localhost:8000/metrics · Prometheus: localhost:9090" },
  { id: "traffic", title: "Send traffic", code: "1..50 | ForEach-Object { Invoke-WebRequest -Uri http://localhost:8000/demo -Method GET }", note: "Switch policy or change a backend mode in the dashboard. Set ROUTEMESH_ADMIN_TOKEN in a local .env to protect admin controls." },
];

export function QuickStartSection() {
  const [copied, setCopied] = useState<string | null>(null);

  async function copy(id: string, value: string) {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(value);
      setCopied(id);
    } catch {
      const code = document.getElementById(`command-${id}`);
      if (code) {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
      }
      setCopied(`selected-${id}`);
    }
    window.setTimeout(() => setCopied(null), 1_600);
  }

  return (
    <section className="section wrap" id="start">
      <div className="section-heading centered"><h2>Running in one command.</h2><p>Needs Docker Desktop with its engine running. The stack starts one proxy, three controllable FastAPI backends, Prometheus, and the dashboard.</p></div>
      <div className="stage quickstart-stage"><ol className="steps-list">
        {commands.map((command,index)=><li key={command.id}>
          <h3><b>{index+1}</b>{command.title}</h3>
          <div className="code-row"><code id={`command-${command.id}`}>{command.code}</code><button type="button" onClick={()=>void copy(command.id,command.code)}>{copied===command.id?"Copied":copied===`selected-${command.id}`?"Selected":"Copy"}</button></div>
          {command.note && <p>{command.note}</p>}
        </li>)}
      </ol></div>
    </section>
  );
}
