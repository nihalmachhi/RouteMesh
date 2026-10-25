const questions = [
  { question: "Is RouteMesh production-ready?", answer: "No. It is a single-process learning system. The backend registry and decision stream live in memory, so run one proxy replica." },
  { question: "How does latency-aware scoring work?", answer: "Latency, CPU, and error rate are normalized among eligible candidates and weighted 0.5, 0.3, and 0.2. A small in-flight penalty is added; the lowest score wins with a stable tie-break. It is an explicit heuristic, not machine learning." },
  { question: "What if every backend is down?", answer: "The proxy returns 503 with a Retry-After header. A forward timeout maps to 504 and a connection failure maps to 502." },
  { question: "Are there benchmark results?", answer: "No measured results are checked in. Run make bench against a running stack to create CSV, JSON, and a p95 chart locally." },
  { question: "Do I need Docker?", answer: "The documented quick start uses Docker Compose. For development, make install, make check, and make test run the Python tooling." },
];

export function FAQSection() {
  return (
    <section className="section wrap" id="faq">
      <div className="section-heading centered"><h2>Questions.</h2></div>
      <div className="faq-list">
        {questions.map((item)=><details key={item.question}><summary>{item.question}</summary><p>{item.answer}</p></details>)}
      </div>
    </section>
  );
}
