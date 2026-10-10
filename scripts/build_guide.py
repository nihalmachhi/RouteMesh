from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "RouteMesh_How_It_Works.pdf"
INK = colors.HexColor("#17212b")
BLUE = colors.HexColor("#145c85")
PALE = colors.HexColor("#eaf3f8")
GREEN = colors.HexColor("#e7f3ed")
GOLD = colors.HexColor("#fff4d6")
MUTED = colors.HexColor("#526170")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=32, textColor=INK, alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="Deck", parent=styles["Normal"], fontSize=12, leading=18, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontSize=19, leading=23, textColor=BLUE, spaceBefore=8, spaceAfter=10))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontSize=12, leading=15, textColor=INK, spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontSize=8, leading=11, textColor=MUTED))
styles.add(ParagraphStyle(name="Cellx", parent=styles["BodyText"], fontSize=8, leading=11, textColor=INK, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="CellBoldx", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=INK, alignment=TA_CENTER))

def p(text, style="Bodyx"):
    return Paragraph(text, styles[style])

def diagram(rows, widths):
    table = Table([[p(cell, "CellBoldx") for cell in row] for row in rows], colWidths=widths, hAlign="CENTER")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), PALE),
        ("BOX", (0,0), (-1,-1), 0.8, BLUE),
        ("INNERGRID", (0,0), (-1,-1), 0.5, colors.white),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 11),
        ("BOTTOMPADDING", (0,0), (-1,-1), 11),
    ]))
    return table

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d9e2e8"))
    canvas.line(0.65*inch, 0.55*inch, 7.85*inch, 0.55*inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.68*inch, 0.36*inch, "RouteMesh | Local learning project")
    canvas.drawRightString(7.82*inch, 0.36*inch, f"{doc.page}")
    canvas.restoreState()

story = []
story += [Spacer(1, 1.0*inch), p("RouteMesh", "CoverTitle"),
          p("How the adaptive reverse proxy works", "Deck"), Spacer(1, 0.25*inch),
          diagram([["CLIENT", "ROUTEMESH PROXY", "SELECTED BACKEND"], ["request", "health + policy + safeguards", "response"]], [1.55*inch, 3.0*inch, 1.55*inch]),
          Spacer(1, 0.35*inch),
          p("A practical guide to starting the system, following a request, understanding the routing choices, and experimenting safely.", "Deck"),
          Spacer(1, 0.7*inch),
          p("<b>What you will learn</b>", "H2x"),
          p("Where each project folder fits; how health checks, routing policies, retries, circuit breakers, and metrics work together; how to start the local stack; and where to look when something goes wrong."),
          p("This guide documents the repository implementation. Benchmark charts and numbers are created from a real local run; none are invented or pre-filled.", "Smallx"),
          PageBreak()]
story += [p("1. A request's journey", "H1x"),
          p("RouteMesh is an HTTP reverse proxy. A client sends a request to the proxy; the proxy chooses one eligible backend, forwards the request, observes the outcome, and returns a safe response. The operations dashboard reads the proxy's admin API and live event stream."),
          diagram([["1. CLIENT", "2. ADMISSION", "3. CANDIDATES", "4. POLICY"], ["HTTP request", "Request-size and concurrency guard", "Healthy + breaker-eligible", "Policy chooses backend"]], [1.5*inch]*4),
          Spacer(1, 7),
          diagram([["5. FORWARD", "6. OBSERVE", "7. RESPOND"], ["HTTPX shared client", "Latency, errors, in-flight, decision reason", "Response or clear 502 / 503 / 504"]], [2.0*inch]*3),
          p("The routing policy is deliberately pure: it sees detached backend snapshots and returns a decision. The router owns mutable state, eligibility, retries, and recording outcomes. This separation makes policy behavior testable without running network calls.", "Bodyx"),
          p("What the policies do", "H2x"),
          p("<b>Round robin</b> rotates through eligible backends. <b>Least connections</b> selects the backend with the fewest current requests. <b>Latency aware</b> scores candidate latency, CPU, error rate, and a small in-flight penalty; the lowest score wins. These are explicit heuristics, not machine learning."),
          p("Resilience in plain terms", "H2x"),
          p("Active health checks remove failing services and restore them after successful recovery checks. A circuit breaker temporarily stops requests to a backend that is repeatedly failing, then allows a probe after its open interval. If no backend can serve, the proxy returns 503 and Retry-After. Safe retries are bounded by a shared budget and only used for idempotent requests or a request carrying an Idempotency-Key."),
          PageBreak(),
          p("2. Folders and responsibilities", "H1x")]
folder_rows = [
    [p("Path", "CellBoldx"), p("Purpose", "CellBoldx")],
    [p("src/routemesh/proxy", "Smallx"), p("FastAPI application, request routing, HTTP forwarding, backpressure, and admin endpoints.", "Smallx")],
    [p("src/routemesh/policies", "Smallx"), p("Round-robin, least-connections, latency-aware policy decisions.", "Smallx")],
    [p("src/routemesh/discovery", "Smallx"), p("Validated static YAML configuration and live backend registry.", "Smallx")],
    [p("src/routemesh/health", "Smallx"), p("Active checks and circuit breaker state transitions.", "Smallx")],
    [p("src/routemesh/metrics", "Smallx"), p("Prometheus metrics, latency/error windows, decision log, and SSE events.", "Smallx")],
    [p("src/routemesh/test_backends", "Smallx"), p("Local demo backends with controls for slow, failing, or unavailable behavior.", "Smallx")],
    [p("src/routemesh/benchmarks", "Smallx"), p("Repeatable Locust workload and comparative report generation.", "Smallx")],
    [p("dashboard/src", "Smallx"), p("Next.js operations dashboard: backend health, policy controls, behavior controls, and decision feed.", "Smallx")],
    [p("configs", "Smallx"), p("Backend routing configuration and Prometheus scrape configuration.", "Smallx")],
    [p("tests", "Smallx"), p("Unit tests for decisions and safeguards plus forwarding integration tests.", "Smallx")],
    [p("docs", "Smallx"), p("Architecture, design decisions, benchmark method/results, and this guide.", "Smallx")],
]
t = Table(folder_rows, colWidths=[1.8*inch, 4.65*inch], repeatRows=1)
t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),PALE),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#c9d6de")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
story += [t, Spacer(1, 8), p("The main process flow is observable at /metrics. The admin API provides current backend state and decisions; server-sent events update the dashboard feed. Metric labels stay bounded and do not include request IDs.", "Bodyx"), PageBreak(),
          p("3. Run the local system", "H1x"),
          p("Requirements: Docker Desktop with its Linux container engine running. Open PowerShell in the RouteMesh project folder."),
          p("<b>1.</b> Create the local environment file: <font name='Courier'>Copy-Item .env.example .env</font>"),
          p("<b>2.</b> Start all services: <font name='Courier'>docker compose up --build</font>"),
          p("<b>3.</b> Open the dashboard at <font name='Courier'>http://localhost:3000</font>. API docs are at <font name='Courier'>http://localhost:8000/docs</font>; Prometheus is at <font name='Courier'>http://localhost:9090</font>."),
          p("<b>4.</b> Send sample traffic in another PowerShell window: <font name='Courier'>1..50 | ForEach-Object { Invoke-WebRequest -Uri http://localhost:8000/demo -Method GET }</font>"),
          p("<b>5.</b> Change the policy or make a backend slow/failing in the dashboard. Watch backend state and the decision feed change. Restore the behavior controls after experimenting."),
          p("<b>6.</b> Stop the stack with <font name='Courier'>docker compose down</font>."),
          p("Useful endpoints", "H2x"),
          p("<b>/healthz</b> checks proxy health. <b>/metrics</b> exposes Prometheus data. <b>/admin/backends</b> lists backend state. The admin policy and behavior controls can modify runtime state; set ROUTEMESH_ADMIN_TOKEN when exposing them beyond a local demo."),
          p("Run developer checks", "H2x"),
          p("Install dependencies using <font name='Courier'>make install</font>. Then run <font name='Courier'>make check</font> for lint, strict type checking, and tests. For measured policy comparison, start the stack and run <font name='Courier'>make bench</font>. It writes raw output and a p95 chart under output/benchmarks and updates docs/benchmarks/results.md. Results depend on your machine and workload; compare runs only when conditions match."),
          PageBreak(),
          p("4. Debugging and boundaries", "H1x"),
          p("If the dashboard cannot connect, check that the proxy is reachable at port 8000 and inspect the browser console. If Docker reports a named-pipe or engine error, launch Docker Desktop and wait for its engine before retrying Compose. If no backends are eligible, inspect the admin backend list and wait for health checks to recover."),
          p("A request timeout returns 504; a backend connection failure returns 502; no eligible backend or admission rejection returns 503. Request IDs are included in response headers and decision data for correlation, but are not Prometheus labels."),
          p("Scope and trade-offs", "H2x"),
          p("The first version uses static YAML discovery and in-memory state. It is designed for a local, single-proxy demonstration, not multi-replica production traffic. It buffers bounded request bodies. TLS termination, HTTP/2, WebSocket proxying, large streaming uploads, and dynamic cloud discovery are outside the current scope."),
          p("Next learning steps", "H2x"),
          p("1. Read docs/architecture.md alongside src/routemesh/proxy/router.py. 2. Trace one request through routes_proxy.py and forwarder.py. 3. Compare policy modules under src/routemesh/policies. 4. Read tests/unit and tests/integration to see expected failure behavior. 5. Run the benchmark only after bringing the stack up."),
          p("Benchmark integrity", "H2x"),
          p("The repository intentionally does not claim measured performance before a real benchmark has run. A generated report should be interpreted as a local experiment, not as a universal production guarantee."),
          Spacer(1, 10),
          p("RouteMesh source: the supplied RouteMesh specification and the implementation in this repository. For exact commands and current settings, use README.md and .env.example.", "Smallx")]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(str(OUTPUT), pagesize=letter, rightMargin=0.65*inch, leftMargin=0.65*inch, topMargin=0.65*inch, bottomMargin=0.75*inch, title="RouteMesh - How It Works", author="RouteMesh Project")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
