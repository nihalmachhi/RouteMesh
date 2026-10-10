import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: { extend: { colors: { ink: "#183247", muted: "#657783", line: "#dbe3e8", accent: "#287a72" } } },
  plugins: [],
};
export default config;
