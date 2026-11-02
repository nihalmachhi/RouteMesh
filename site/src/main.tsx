import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/instrument-sans";
import "@fontsource/jetbrains-mono/400.css";
import "./styles/base.css";
import "./styles/site.css";
import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);