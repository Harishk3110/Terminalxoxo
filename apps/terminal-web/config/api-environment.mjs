import { isIP } from "node:net";

export function apiOrigin(env = process.env) {
  const appEnv = env.NEXT_PUBLIC_APP_ENV || env.KNK_ENV || env.NODE_ENV;
  const local = env.VERCEL !== "1" && ["local", "local-demo", "development", "test"].includes(appEnv);
  const configured = env.KNK_API_URL || env.NEXT_PUBLIC_API_BASE_URL;
  if (!configured && !local) {
    throw new Error("Set KNK_API_URL to the public HTTPS FastAPI origin before deploying the terminal. No hosted demo API fallback exists.");
  }
  const url = new URL(configured || "http://127.0.0.1:8000");
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new Error("KNK_API_URL must be an HTTP(S) origin without credentials, path, query or fragment.");
  }
  const host = url.hostname.replace(/^\[|\]$/g, "").toLowerCase().replace(/\.$/, "");
  const ip = isIP(host);
  const privateV4 = ip === 4 && /^(0\.|10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host);
  const privateV6 = ip === 6 && (host === "::1" || host === "::" || /^(fc|fd|fe[89ab]|::ffff:)/.test(host));
  if (!local && (url.protocol !== "https:" || privateV4 || privateV6 || !host.includes(".") && ip !== 6 || /\.(localhost|local|internal)$/.test(host))) {
    throw new Error("Hosted terminal builds require a public HTTPS API origin; loopback and private-network addresses are not allowed.");
  }
  return url.origin;
}
